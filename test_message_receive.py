import unittest
import json
from message_receive import message_receive

class TestMessageReceive(unittest.TestCase):

    def test_extended_text_message(self):
        data = {
            'Info': {
                'Chat': '120363318028761250@g.us',
                'Sender': '16467338252:17@s.whatsapp.net',
                'IsFromMe': False,
                'IsGroup': True,
                'BroadcastListOwner': '',
                'ID': '3EB062089F7D33F93DEF36',
                'ServerID': 0,
                'Type': 'text',
                'PushName': 'Anton',
                'Timestamp': '2024-11-05T22:30:13Z',
                'Category': '',
                'Multicast': False,
                'MediaType': '',
                'Edit': '',
                'MsgBotInfo': {
                    'EditType': '',
                    'EditTargetID': '',
                    'EditSenderTimestampMS': '0001-01-01T00:00:00Z'
                },
                'MsgMetaInfo': {
                    'TargetID': '',
                    'TargetSender': ''
                },
                'VerifiedName': None,
                'DeviceSentMeta': None
            },
            'Message': {
                'extendedTextMessage': {
                    'text': 'You did, I saw that - thank you!  What I’m yet to crack the nut on is how to get people to actually contribute to it.',
                    'contextInfo': {
                        'stanzaID': '3AA443B8FA81C56E8BEE',
                        'participant': '50662536248@s.whatsapp.net',
                        'quotedMessage': {
                            'conversation': 'I did post the website as a resource but it may have gotten lost in the chatter.',
                            'messageContextInfo': {
                                'messageSecret': 'zB4xvGlj4yxNAT8+Of47dpkpoFU/znfjF74jWmwqnzM='
                            }
                        }
                    },
                    'inviteLinkGroupTypeV2': 0
                },
                'messageContextInfo': {
                    'messageSecret': 'pn4D5/J9P8Db0/ZTHSKZQy9g88t/jv1QXPdpg3lQuYc='
                }
            },
            'IsEphemeral': False,
            'IsViewOnce': False,
            'IsViewOnceV2': False,
            'IsViewOnceV2Extension': False,
            'IsDocumentWithCaption': False,
            'IsLottieSticker': False,
            'IsEdit': False,
            'SourceWebMsg': None,
            'UnavailableRequestID': '',
            'RetryCount': 0,
            'NewsletterMeta': None,
            'RawMessage': {
                'extendedTextMessage': {
                    'text': 'You did, I saw that - thank you!  What I’m yet to crack the nut on is how to get people to actually contribute to it.',
                    'contextInfo': {
                        'stanzaID': '3AA443B8FA81C56E8BEE',
                        'participant': '50662536248@s.whatsapp.net',
                        'quotedMessage': {
                            'conversation': 'I did post the website as a resource but it may have gotten lost in the chatter.',
                            'messageContextInfo': {
                                'messageSecret': 'zB4xvGlj4yxNAT8+Of47dpkpoFU/znfjF74jWmwqnzM='
                            }
                        }
                    },
                    'inviteLinkGroupTypeV2': 0
                },
                'messageContextInfo': {
                    'messageSecret': 'pn4D5/J9P8Db0/ZTHSKZQy9g88t/jv1QXPdpg3lQuYc='
                }
            }
        }
        response = message_receive(data)
        response_body = json.loads(response['body'])
        self.assertEqual(response_body['text'], 'You did, I saw that - thank you!  What I’m yet to crack the nut on is how to get people to actually contribute to it.')

    def test_conversation_message(self):
        data = {
            'Info': {
                'Chat': '120363348507910736@g.us',
                'Sender': '16467338252@s.whatsapp.net',
                'IsFromMe': False,
                'IsGroup': True,
                'BroadcastListOwner': '',
                'ID': '3AAD304A502513CDE821',
                'ServerID': 0,
                'Type': 'text',
                'PushName': 'Anton',
                'Timestamp': '2024-11-05T16:57:19Z',
                'Category': '',
                'Multicast': False,
                'MediaType': '',
                'Edit': '',
                'MsgBotInfo': {
                    'EditType': '',
                    'EditTargetID': '',
                    'EditSenderTimestampMS': '0001-01-01T00:00:00Z'
                },
                'MsgMetaInfo': {
                    'TargetID': '',
                    'TargetSender': ''
                },
                'VerifiedName': None,
                'DeviceSentMeta': None
            },
            'Message': {
                'conversation': 'Speed test',
                'messageContextInfo': {
                    'messageSecret': 'IvUE8gICzVqC+5nXv97KguA8lJwQuNISPStqqCELjE4='
                }
            },
            'IsEphemeral': False,
            'IsViewOnce': False,
            'IsViewOnceV2': False,
            'IsViewOnceV2Extension': False,
            'IsDocumentWithCaption': False,
            'IsLottieSticker': False,
            'IsEdit': False,
            'SourceWebMsg': None,
            'UnavailableRequestID': '',
            'RetryCount': 0,
            'NewsletterMeta': None,
            'RawMessage': {
                'conversation': 'Speed test',
                'messageContextInfo': {
                    'messageSecret': 'IvUE8gICzVqC+5nXv97KguA8lJwQuNISPStqqCELjE4='
                }
            }
        }
        response = message_receive(data)
        response_body = json.loads(response['body'])
        self.assertEqual(response_body['text'], 'Speed test')

if __name__ == '__main__':
    unittest.main()