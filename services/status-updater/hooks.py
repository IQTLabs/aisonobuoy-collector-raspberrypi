import os
import time

import httpx


def get_url():
    return os.getenv("WEBHOOK_URL", "")

def get_webhook_token():
    return os.getenv("WEBHOOK_TOKEN","")

def message_card_template():
    timestamp = int(time.time())
    card = {
        "@type": "MessageCard",
        "@context": "https://schema.org/extensions",
        "summary": f"Status Update - {timestamp}",
        "themeColor": "1b9e77",
        "title": "",
        "sections": [
            {
                "activityTitle": "",
                "activitySubtitle": "",
                "facts": [],
                "text": ""
            }
        ]
    }

    return card

def insert_message_data(data):
    card = message_card_template()
    # set card title
    card['title'] = data['title']

    # change theme color
    if 'themeColor' in data:
        card['themeColor'] = data['themeColor']

    # set card body title
    card['sections'][0]['activityTitle'] = data['body_title']

    # set card body subtitle
    card['sections'][0]['activitySubtitle'] = data['body_subtitle']

    # set body text
    card['sections'][0]['text'] = data['text']

    # add list of card facts
    card['sections'][0]['facts'] = data['facts']

    return card

def send_hook(card):
    try:
        headers = {}
        webhook_token = get_webhook_token()
        if webhook_token is not None and webhook_token != "":
            headers = {'Device-Token': webhook_token}

        r = httpx.post(get_url(), headers=headers, json=card, timeout=5.0)
        return r.status_code
    except Exception as e:
        return f'Failed because: {e}, on card: {card}'
