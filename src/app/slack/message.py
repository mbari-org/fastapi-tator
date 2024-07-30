# fastapi-tator, Apache-2.0 license
# Filename: app/slack/message.py
# Description: slack message creation


from datetime import datetime


def create_message(dt: datetime, mission: str, detections: dict) -> [dict]:
    if 'whale' in detections:
        summary = f":whale: *{detections['whale']}* detections of whales"
    if 'dolphin' in detections:
        summary += f"\n\n:dolphin: *{detections['dolphin']}* detections of dolphins"
    if 'seal' in detections:
        summary += f"\n\n:seal: *{detections['seal']}* detections of seals"
    if 'bird' in detections:
        summary += f"\n\n:bird: *{detections['bird']}* detections of birds"
    if 'boat' in detections:
        summary += f"\n\n:boat: *{detections['boat']}* detections of boats"
    if 'shark' in detections:
        summary += f"\n\n:shark: *{detections['shark']}* detections of sharks"
    if 'kelp' in detections:
        summary += f"\n\n:kelp: *{detections['kelp']}* detections of kelp"

    # Only include the mission name up to the T
    mission_start = mission.split('T')[0]

    blocks = [{
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": f":plane: Hello UAV Members! \n*{mission}* mission has finished processing at {dt}\\n\n "
        }
    },
        {
            "type": "divider"
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": summary
            }
        },
        {
            "type": "divider"
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Review detections in Mantis",
                        "emoji": True
                    },
                    "value": "click_me_123",
                    "url": f"http://mantis.shore.mbari.org/4/analytics/localizations?filterConditions=%255B%257B%2522category%2522%253A%2522Image%2522%252C%2522field%2522%253A%2522%2524name%2522%252C%2522modifier%2522%253A%2522Starts%2520with%2522%252C%2522value%2522%253A%2522{mission_start}%2522%252C%2522categoryGroup%2522%253A%2522Media%2522%257D%255D&pageSize=50&page=1&lock=1",
                }
            ]
        }]
    return blocks
