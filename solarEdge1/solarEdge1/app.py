import boto3
from botocore.exceptions import ClientError
import solaredge
import pandas, datetime, json
import base64

def get_secrets():
    """Returns the SolarEdge API key and the Gmail API Key"""

    secret_name = "solarmonitoring"
    region_name = "eu-west-1"

    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(service_name='secretsmanager', region_name=region_name)

    # In this sample we only handle the specific exceptions for the 'GetSecretValue' API.
    # See https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_GetSecretValue.html
    # We rethrow the exception by default.

    try:
        get_secret_value_response = client.get_secret_value(SecretId=secret_name)
        print("get_secret_value_response=",get_secret_value_response)
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            print("The requested secret " + secret_name + " was not found")
        elif e.response['Error']['Code'] == 'InvalidRequestException':
            print("The request was invalid due to:", e)
        elif e.response['Error']['Code'] == 'InvalidParameterException':
            print("The request had invalid params:", e)
        else:
            print("unhandled exception e.response[Error][Code]= ", e.response['Error']['Code'])
    else:
        # Decrypts secret using the associated KMS CMK.
        # Depending on whether the secret is a string or binary, one of these fields will be populated.
        if 'SecretString' in get_secret_value_response:
            secret = get_secret_value_response['SecretString']
        else:
            decoded_binary_secret = base64.b64decode(get_secret_value_response['SecretBinary'])

    pws = eval(get_secret_value_response['SecretString'])
    # print(pws)
    print (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S %Z"), pws["solarEdge"],pws["emailPW"])
    return (pws["solarEdge"],pws["emailPW"])

def initializeAPI(api_key):
    print (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S %Z"), "In initializeAPI")
    api = solaredge.Solaredge(api_key)
    print(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S %Z"), "After initialization")
    return api

def minsSinceLastUpdate(connectionKey, site_key):
    """
    Returns an integer indicating the number of minutes since the SolarEdge equipment reported back
    to SolarEdge's servers

    returns number of minutes since last update
    """
    get_overview_resp = connectionKey.get_overview(site_key)
    latest = get_overview_resp['overview']['lastUpdateTime']
    print(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S %Z"), "Latest=",latest)
    return ((datetime.datetime.now()  -datetime.datetime.strptime(latest,"%Y-%m-%d %H:%M:%S")).seconds)/60

def sendEmail (sender, pw,  addressee, subject, body):
    import smtplib
    from email.message import EmailMessage

    msg = EmailMessage()
    msg.set_content(body)

    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = addressee

    try:
        # Send the message via our own SMTP server.
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(sender, pw)
        server.send_message(msg)
        print (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S %Z"), ": mail sent")
        server.quit()
    except:
        print ('Something went wrong...')

def lambda_handler(environ, start_response):
# if __name__ == "__main__":
# path = environ['PATH_INFO']
# method = environ['REQUEST_METHOD']
# Constants
    errorThreshold = 2
    site_key = 25501
    (solarEdgepw, gmailPW) = get_secrets()
    connection = initializeAPI(solarEdgepw)
    interval = minsSinceLastUpdate(connection, site_key)
    print (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S %Z"), ": interval was ", str(round(interval,1)),
           " minutes (Error threshold =",str(round(errorThreshold,0)),"minutes)")
    if (interval > errorThreshold):
        print (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S %Z"), ": sending mail")
        sendEmail("davidsamson.efrat@gmail.com", gmailPW, addressee="davidsamson.efrat@gmail.com",
                    subject="No solar reports in " +str(round(interval,1))+ " minutes", body="Get on it")


