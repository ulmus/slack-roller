import boto3
from base64 import b64decode
from urlparse import parse_qs
import logging
import json
import re
import random
import sys

ENCRYPTED_EXPECTED_TOKEN = "" # Insert encrypted token here

kms = boto3.client('kms')
expected_token = kms.decrypt(CiphertextBlob = b64decode(ENCRYPTED_EXPECTED_TOKEN))['Plaintext']

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
    
    result_text = roll_dice_notation_and_return_result(command_text)
    return {
        "response_type": "in_channel",
        "text": "%s is rolling %s" % (user, command_text),
        "attachments": [
            {
                "text": result_text
            }
        ]
    }

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
		die_type = int(result.group(3))
		try:
			modifier = int(result.group(4))
		except (IndexError, TypeError):
			modifier = 0
	except (IndexError, TypeError):
		raise DiceRollerException(u"No correct dice roller notation found in '%s', use '/roll 2d6+1' or similar syntax" % dice_notation)
	if num_dice > 1000:
		raise DiceRollerException(u"You may only roll a maximum of 1000 dice at a time")
	return [num_dice, die_type, modifier]


def roll_dice(num_dice, die_type):
	return [random.randint(1, die_type) for i in xrange(num_dice)]


def generate_dice_roll_text(dice_notation, rolled_dice, modifier):
	return u"For your convenience, I've rolled %(dice_notation)s, the dice turning up [%(rolled_dice)s] for a sum of %(sum)s" % {
		"dice_notation" : dice_notation,
		"rolled_dice" : u", ".join([unicode(die) for die in rolled_dice]),
		"sum" : sum(rolled_dice) + modifier,
	}
	
def roll_dice_notation_and_return_result(dice_notation):
	try:
		parsed_dice = parse_dice_notation(dice_notation)
	except DiceRollerException as e:
		return unicode(e)
	rolled_dice = roll_dice(parsed_dice[0], parsed_dice[1])
	return generate_dice_roll_text(dice_notation, rolled_dice, parsed_dice[2])
	
	
def main():
	dice_notation_entered = sys.argv[1]
	parsed_dice = parse_dice_notation(dice_notation_entered)
	rolled_dice = roll_dice(parsed_dice[0], parsed_dice[1])
	print generate_dice_roll_text(dice_notation_entered, rolled_dice, parsed_dice[2])


if __name__ == "__main__":
    main()