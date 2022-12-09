"""
PiBackbone module for install the basic required subsystems on a Pi-based project
"""
import argparse
import json
import logging
import os
import sys

#import docker
from plumbum import FG  # pytype: disable=import-error
from plumbum import local  # pytype: disable=import-error
from plumbum import TF  # pytype: disable=import-error
from plumbum.cmd import chmod  # pytype: disable=import-error # pylint: disable=import-error
from plumbum.cmd import chown  # pytype: disable=import-error # pylint: disable=import-error
from plumbum.cmd import cp  # pytype: disable=import-error # pylint: disable=import-error
from plumbum.cmd import docker_compose  # pytype: disable=import-error # pylint: disable=import-error
from plumbum.cmd import echo  # pytype: disable=import-error # pylint: disable=import-error
from plumbum.cmd import mkdir  # pytype: disable=import-error # pylint: disable=import-error
from plumbum.cmd import reboot  # pytype: disable=import-error # pylint: disable=import-error
from plumbum.cmd import shutdown  # pytype: disable=import-error # pylint: disable=import-error
from plumbum.cmd import sudo  # pytype: disable=import-error # pylint: disable=import-error
from plumbum.cmd import tee  # pytype: disable=import-error # pylint: disable=import-error
from InquirerPy import prompt

from pibackbone import __file__
from pibackbone import __version__
from pibackbone.styles import custom_style


level_int = {'CRITICAL': 50, 'ERROR': 40, 'WARNING': 30, 'INFO': 20,
             'DEBUG': 10}
level = level_int.get(os.getenv('LOGLEVEL', 'INFO').upper(), 0)
format = '%(message)s'
logging.basicConfig(format=format, level=level)


class bcolors:
    """
    Colors from: https://svn.blender.org/svnroot/bf-blender/trunk/blender/build_files/scons/tools/bcolors.py
    """
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


class PiBackbone():
    """
    Main PiBackbone class for install the basic required subsystems on a Pi-based project
    """
    def __init__(self, raw_args=None):
        self.raw_args = raw_args
        self.previous_dir = os.getcwd()
        self.definitions = {}
        self.services = []
        self.projects = []

    @staticmethod
    def execute_prompt(questions):
        """
        Run end user prompt with supplied questions and return the selected
        answers
        """
        answers = prompt(questions, style=custom_style)
        return answers

    @staticmethod
    def initial_question():
        """Ask which if starting a project"""
        return [
            {
                'type': 'confirm',
                'name': 'existing_project',
                'message': 'Do you want to run a pre-existing project?',
                'default': False,
            },
        ]

    def project_question(self):
        """Ask which project to start"""
        return [
            {
                'type': 'list',
                'name': 'project',
                'message': 'What project would you like to build?',
                'choices': self.projects,
            },
        ]

    def services_question(self):
        """Ask which services to start"""
        service_choices = []
        for service in self.services:
            service_choices.append({'name': service, 'value': service})
        return [
            {
                'type': 'checkbox',
                'name': 'services',
                'message': 'What services would you like to start?',
                'choices': service_choices,
            },
        ]

    def quit(self):
        """Reset the working directory and exit the program"""
        self.reset_cwd()
        sys.exit(1)

    @staticmethod
    def _check_conf_dir(conf_dir):
        """Check the conf directory is valid"""
        realpath = os.path.realpath(conf_dir)
        if not realpath.endswith('/pibackbone'):
            raise ValueError(
                f'last element of conf_dir must be pibackbone: {realpath}')
        for valid_prefix in ('/usr/local', '/opt', '/home', '/Users'):
            if realpath.startswith(valid_prefix):
                return realpath
        raise ValueError(f'conf_dir root may not be safe: {realpath}')

    def set_config_dir(self, conf_dir='/opt/pibackbone'):
        """Set the current working directory to where the configs are"""
        try:
            realpath = self._check_conf_dir(
                os.path.dirname(__file__).split('lib')[0] + conf_dir)
            os.chdir(realpath)
        except Exception as err:  # pragma: no cover
            logging.error(
                '%sUnable to find config files, exiting because: %s%s', bcolors.FAIL, err, bcolors.ENDC)
            self.quit()

    def reset_cwd(self):
        """Set the current working directory back to what it was originally"""
        os.chdir(self.previous_dir)

    def get_definitions(self):
        """Get definitions of services and projects"""
        with open('definitions.json', 'r') as file_handler:
            self.definitions = json.load(file_handler)
            self.services = self.definitions['services']
            self.projects = list(self.definitions['projects'])
            self.projects.append('None')

    def menu(self):
        """Drive the menu interface"""
        answer = self.execute_prompt(self.initial_question())
        if 'existing_project' in answer and answer['existing_project']:
            answer = self.execute_prompt(self.project_question())
        else:
            answer = self.execute_prompt(self.services_question())
        return answer

    @staticmethod
    def aws_questions():
        """Ask for AWS credentials"""
        return [
            {
                'type': 'password',
                'message': 'Enter your AWS Access Key ID',
                'name': 'aws_access_key_id'
            },
            {
                'type': 'password',
                'message': 'Enter your AWS Secret Access Key',
                'name': 'aws_secret_access_key'
            },
        ]

    @staticmethod
    def env_questions(envs):
        """Ask for environment variable values"""
        questions = []
        for env in envs:
            question = {}
            question['type'] = 'input'
            question['name'] = env[0]
            question['message'] = f'Would you like to set the environment variable for: {env[0]}?'
            question['default'] = env[1]
            questions.append(question)
        return questions

    @staticmethod
    def core_services_question():
        """Ask if running core services"""
        return [
            {
                'type': 'confirm',
                'name': 'core_services',
                'message': 'Do you want to run a core services (watchtower, etc.) alongside your choices?',
                'default': True,
            },
        ]

    @staticmethod
    def reboot_question():
        """Ask if they would like to reboot the machine"""
        return [
            {
                'type': 'list',
                'name': 'reboot_machine',
                'message': 'Do you want to reboot or shutdown this machine now? (Recommended as some changes require a reboot to take effect)',
                'choices': ['Reboot', 'Shutdown', 'None'],
            },
        ]

    def parse_answer(self, answer):
        """Parse out answer"""
        services = []
        project = ""
        if 'project' in answer:
            if answer['project'] == 'None':
                logging.info('%sNothing chosen, quitting.%s', bcolors.OKCYAN, bcolors.ENDC)
                self.quit()
            project = answer['project']
            services = self.definitions['projects'][project]['services']
            logging.info('The project %s%s%s uses the following services:\n', bcolors.OKGREEN, project, bcolors.ENDC) 
            for service in services:
                logging.info('%s%s%s', bcolors.OKGREEN, service, bcolors.ENDC)
        elif 'services' in answer:
            if not answer['services']:
                logging.info('%sNothing chosen, quitting.%s', bcolors.OKCYAN, bcolors.ENDC)
                self.quit()
            for service in answer['services']:
                services.append(service)
        else:
            logging.error('%sInvalid choices in answer: %s%s', bcolors.FAIL, answer, bcolors.ENDC)
            self.quit()
        return services, project

    def install_requirements(self, services):
        """Install requirements of choices made"""
        config = []
        install = []
        logging.info('%sInstalling requirements for services into /etc/cron.d/ and /boot/config.txt...%s', bcolors.OKCYAN, bcolors.ENDC)
        for service in services:
            if 'config' in self.services[service]:
                config += self.services[service]['config']
            if 'install' in self.services[service]: 
                install += self.services[service]['install']
            if os.path.exists(f'scripts/{service}'):
                sudo[cp[f'scripts/{service}', f'/etc/cron.d/{service}']]
        for entry in config:
            chain = echo[entry] | sudo[tee["-a", "/boot/config.txt"]]
            chain()
        current_dir = os.getcwd() 
        os.chdir('/tmp')
        for entry in install:
            os.system(entry)
        os.chdir(current_dir)

    def apply_secrets(self, services):
        """Set secret information specific to the deployment"""
        logging.info('%sApplying secrets and system specific variables...%s', bcolors.OKCYAN, bcolors.ENDC)
        if 's3-upload' in services:
            aws_dir = os.path.join('/root', '.aws')
            if not os.path.exists(os.path.join(aws_dir, 'credentials')):
                answer = self.execute_prompt(self.aws_questions())
                aws_id = ""
                aws_secret = ""
                if 'aws_access_key_id' in answer:
                    aws_id = answer['aws_access_key_id']
                if 'aws_secret_access_key' in answer:
                    aws_secret = answer['aws_secret_access_key']
                sudo[mkdir['-p', aws_dir]]()
                sudo[chmod['777', '/root']]()
                sudo[chmod['-R', '777', aws_dir]]()
                with open(os.path.join(aws_dir, 'credentials'), 'w') as f: 
                    f.write(f'[default]\naws_access_key_id = {aws_id}\naws_secret_access_key = {aws_secret}') 
                aws_id = ""
                aws_secret = ""
                answer = None
                with open(os.path.join(aws_dir, 'config'), 'w') as f:
                    f.write("[default]\nregion = us-east-1\noutput = json")
                sudo[chown['-R', 'root:root', aws_dir]]()
                sudo[chmod['700', '/root']]()
                sudo[chmod['750', aws_dir]]()
                sudo[chmod['600', os.path.join(aws_dir, 'credentials')]]()
                sudo[chmod['600', os.path.join(aws_dir, 'config')]]()

        envs = []
        sudo[chmod['666', 'services/.env']]()
        with open('services/.env', 'r') as f:
            for line in f:
                envs.append(line.strip().split('='))
        answer = self.execute_prompt(self.env_questions(envs))
        with open('services/.env', 'w') as f:
            for env in envs:
                if env[0] in answer:
                    f.write(f'{env[0]}={answer[env[0]]}\n')
                else:
                    f.write(f'{env[0]}={env[1]}\n')

    def start_services(self, services):
        """Start services that were requested"""
        compose_files = []
        answer = self.execute_prompt(self.core_services_question())
        if 'core_services' in answer and answer['core_services']:
            compose_files += ['-f', 'docker-compose-core.yml']
        for service in services:
            compose_files += ['-f', f'docker-compose-{service}.yml']
        compose_files += ['up', '-d']
        logging.info('%sStarting services...%s', bcolors.OKCYAN, bcolors.ENDC)
        with local.cwd(local.cwd / 'services'):
            try:
                sudo[docker_compose.bound_command(compose_files)] & FG
            except Exception as e:
                print(f'Failed to start services (though this is likely due to the system needing a reboot before they will work): {e}')

    def output_notes(self, project):
        """Output any notes if a project was chosen and has notes"""
        logging.info('%s%s%s', bcolors.HEADER, self.definitions["projects"][project]["notes"], bcolors.ENDC)

    @staticmethod
    def restart():
        """Restart the machine"""
        logging.warning('%sRebooting now!%s', bcolors.WARNING, bcolors.ENDC)
        sudo[reboot]()

    @staticmethod
    def shutdown():
        """Shutdown the machine"""
        logging.warning('%sShutting down now!%s', bcolors.WARNING, bcolors.ENDC)
        sudo[shutdown['-h', 'now']]()


    def main(self):
        """Main entrypoint to the class, parse args and main program driver"""
        parser = argparse.ArgumentParser(prog='PiBackbone',
                                         description='PiBackbone - A tool for installing the basic required subsystems on a Pi-based project')
        # TODO add option to self update pibackbone
        parser.add_argument('--version', '-V', action='version',
                            version=f'%(prog)s {__version__}')
        args = parser.parse_args(self.raw_args)
        self.set_config_dir()
        self.get_definitions()
        services, project = self.parse_answer(self.menu())
        self.install_requirements(services)
        self.apply_secrets(services)
        self.start_services(services)
        if project:
            self.output_notes(project)
        self.reset_cwd()

        answer = self.execute_prompt(self.reboot_question())
        if 'reboot_machine' in answer:
            if answer['reboot_machine'] == 'Reboot':
                self.restart()
            elif answer['reboot_machine'] == 'Shutdown':
                self.shutdown()
