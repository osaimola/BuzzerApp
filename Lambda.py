import os
import base64
import hashlib
import hmac
import json
import urllib
from twilio.request_validator import RequestValidator
import boto3


def lambda_handler(event, context):
    print("received: " + str(event))

    # specify file paths and names for s3 bucket
    # temp_filename will temporarily hold downloads for processing
    # lampda_path will hold data for upload
    bucket = "buzz-bucket"
    file_name = "hello.txt"
    s3_path = "/" + file_name
    temp_filename = "/tmp/boxx.txt"
    lambda_path = "/tmp/" + file_name

    # create_file takes a string content and saves it to a file specified in path
    def create_file(content, path):
        with open(path, 'w+') as file:
            file.write(content)
            file.close()

    # read_file takes a file path and returns the string content of the file
    def read_file(path):
        temp_string = ""
        with open(path, 'r') as file:
            for line in file:
                temp_string += line + " "
            file.close()
        return temp_string

    # if this request cames from a call and has DTMF tones in Digits
    if "Digits" in event:
        access_code = event['Digits']
        pass_string = ""

        # if master code, unlock
        if access_code == os.environ['MASTER_CODE']:
            return 'master'

        # if 0 is passed request for access
        elif access_code == '0':
            return 'guest'

        # if one time passcode; verify, delete code from passcode list and unlock
        else:
            # read key file from s3
            s3 = boto3.client('s3')
            s3.download_file(bucket, s3_path, temp_filename)
            pass_string += read_file(temp_filename)

            # convert pass_string to list called 'otp'
            otp = pass_string.split(" ")
            print(otp)

            if access_code in otp:
                # delete the one time pass from list
                otp.remove(access_code)
                pass_string = " ".join(otp)
                # update and write file to s3
                create_file(pass_string, lambda_path)
                response = s3.upload_file(lambda_path, bucket, s3_path)
                return 'friend'

            else:
                return 'stranger'

    # if no Digits and request from twilio via authorized number,
    # this is a CREATE< READ< DELETE request. create a validator & parse data
    elif u'twilioSignature' in event and u'Body' in event and event['From'] == os.environ['MY_NUMBER']:

        form_parameters = {
            key: urllib.parse.unquote_plus(value) for key, value in event.items()
            if key != u'twilioSignature'
        }

        validator = RequestValidator(os.environ['AUTH_TOKEN'])

        # validate api call is from twilio
        request_valid = validator.validate(
            os.environ['REQUEST_URL'],
            form_parameters,
            event[u'twilioSignature']
        )

        # if request valid, process text
        if request_valid:
            rawmsg = form_parameters['Body']
            msg = rawmsg.split(" ")

            if msg[0] == "CREATE":
                # add code to file
                pass_string = msg[1] + " "
                s3 = boto3.client('s3')
                s3.download_file(bucket, s3_path, temp_filename)

                pass_string += read_file(temp_filename)

                create_file(pass_string, lambda_path)
                response = s3.upload_file(lambda_path, bucket, s3_path)

                return '<?xml version=\"1.0\" encoding=\"UTF-8\"?>' \
                    '<Response><Message>Key created!</Message></Response>'

            elif msg[0] == "READ":
                print("we reading")
                # download and return all active codes
                pass_string = ""
                s3 = boto3.client('s3')
                s3.download_file(bucket, s3_path, temp_filename)

                pass_string += read_file(temp_filename)

                print("read success!")
                print(pass_string)
                return '<?xml version=\"1.0\" encoding=\"UTF-8\"?>' \
                    f'<Response><Message>Active Keys: {pass_string}</Message></Response>'

            elif msg[0] == "DELETE":
                print("hmm interesting")
                # delete provided code
                pass_string = ""
                s3 = boto3.client('s3')
                s3.download_file(bucket, s3_path, temp_filename)

                pass_string += read_file(temp_filename)

                passes = pass_string.split(" ")
                print(passes)
                if msg[1] in passes:
                    passes.remove(msg[1])
                    pass_string = " ".join(passes)
                    create_file(pass_string, lambda_path)
                    response = s3.upload_file(lambda_path, bucket, s3_path)

                    return '<?xml version=\"1.0\" encoding=\"UTF-8\"?>' \
                        f'<Response><Message>{msg[1]} deleted!</Message></Response>'

                else:
                    return '<?xml version=\"1.0\" encoding=\"UTF-8\"?>' \
                        f'<Response><Message>Key {msg[1]} Not Found!</Message></Response>'

        # if request is not from twilio, give appropriate response
        else:
            return '<?xml version=\"1.0\" encoding=\"UTF-8\"?>' \
                   '<Response><Message>Nice Try...</Message></Response>'
