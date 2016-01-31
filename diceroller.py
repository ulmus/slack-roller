ENCRYPTED_EXPECTED_TOKEN = "" # Insert encrypted token here

from base64 import b64decode
from urlparse import parse_qs
import logging
import json
import re
import random
import sys

try:
	import boto3
	kms = boto3.client('kms')
	expected_token = kms.decrypt(CiphertextBlob = b64decode(ENCRYPTED_EXPECTED_TOKEN))['Plaintext']
except ImportError:
	pass
	
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    req_body = event['body']
    params = parse_qs(req_body)
    token = params['token'][0]
    if token != expected_token:
        logger.error("Request token (%s) does not match exptected", token)
        raise Exception("Invalid request token")

    try:
        user = params['user_name'][0]
        command = params['command'][0]
        channel = params['channel_name'][0]
        command_text = params['text'][0]
    except (KeyError, IndexError):
        return "No dice roller notation provided, use '/roll 2d6+1' or similar syntax"
    
	return roll_dice_notation_and_return_response(user, command_text)

dice_pattern = re.compile("^(\\d+)([dD])(\\d+)(([-+*/])(\\d+))*$")

class DiceRollerException(Exception):
	pass
	
def parse_dice_notation(dice_notation):
	if not dice_notation:
		raise DiceRollerException(u"No dice roller notation provided, use '/roll 2d6+1' or similar syntax")
	dice_notation = dice_notation.strip() # remove whitespace
	result = re.match(dice_pattern, dice_notation)
	if result is None:
		raise DiceRollerException(u"No correct dice roller notation found in '%s', use '/roll 2d6+1' or similar syntax" % dice_notation)
	try:
		num_dice = int(result.group(1))
	except (IndexError, TypeError):
		num_dice = 1
	try:
		die_type = int(result.group(3))
	except (IndexError, TypeError):
		raise DiceRollerException(u"No correct dice roller notation found in '%s', use '/roll 2d6+1' or similar syntax" % dice_notation)
	try:
		modifier = int(result.group(4))
	except (IndexError, TypeError):
		modifier = 0
	if num_dice > 1000:
		raise DiceRollerException(u"You may only roll a maximum of 1000 dice at a time")
	if die_type > 1000:
		raise DiceRollerException(u"The largest die that can be rolled is a D1000")
	return [num_dice, die_type, modifier]


def roll_dice(num_dice, die_type):
	return sorted([random.randint(1, die_type) for i in xrange(num_dice)])


def generate_dice_roll_response(user, dice_notation, dice_num, dice_type, modifier, rolled_dice ):
	return {
        "response_type": "in_channel",
        "text": "%s is rolling %s" % (user, dice_notation),
        "attachments": [
			{
				"title" : "Result",
				"fields" : [
					{
						"title": "Dice rolls",
						"value": format_dice(rolled_dice, dice_type)
					},
					{
						"title": "Sum",
						"value": unicode(get_sum(rolled_dice, modifier))
					}
				]
			}
        ]
    }
	
def get_sum(rolled_dice, modifier):
	return sum(rolled_dice) + modifier
	
def format_dice(rolled_dice, die_type):
	return u", ".join([format_die(die, die_type) for die in rolled_dice])
	
def format_die(die_result, die_type):
	die_text = unicode(die_result)
	if die_result == 1:
		die_text = "_%s_" % die_text
	if die_result == die_type:
		die_text = "*%s*" % die_text 
	return die_text

def roll_dice_notation_and_return_response(user, dice_notation):
	try:
		parsed_dice = parse_dice_notation(dice_notation)
	except DiceRollerException as e:
		return unicode(e)
	rolled_dice = roll_dice(parsed_dice[0], parsed_dice[1])
	return generate_dice_roll_response(user=user, dice_notation=dice_notation, dice_num=parsed_dice[0], dice_type=parsed_dice[1], modifier=parsed_dice[2], rolled_dice=rolled_dice)
	
	
def main():
	dice_notation_entered = sys.argv[1]
	print roll_dice_notation_and_return_response(user = "System", dice_notation= dice_notation_entered)


if __name__ == "__main__":
    main()