import json
import boto3

def lambda_handler(event, context):
    # TODO implement
    #print(event)
    name = event['Records'][0]['s3']['object']['key']
    #name = "bus.jpg"
    
    #================ rekognition - acquire labels ====================
    client = boto3.client('rekognition')
    response = client.detect_labels(
        Image={
            'S3Object': {
                'Bucket': 'hw3-photo-bucket',
                'Name': name
            }
        },
        MaxLabels=5
    )
    labels = []
    for value in response['Labels']:
        labels.append(value['Name'].lower())
    print(labels)
    
    #================ lex - add values in the slot (photoType) ====================
    
    client = boto3.client('lex-models')
    
    # get checksum (params used later)
    response = client.get_slot_type(
        name='photoType',
        version='$LATEST',
    )
    checksum = response["checksum"]
    
    # read current slot type values, then update
    enumerationValues = response['enumerationValues']   # [{'value': 'mammal'}, {'value': 'pillow'}, {'value': 'canine'}, {'value': 'dog'}, {'value': 'pet'}]
    existed_values = set(d['value'] for d in enumerationValues)
    new_values = set(labels)
    values = existed_values | new_values

    enumerationValues = [{'value': v} for v in values]
    print(enumerationValues)
    
    # update(replace) slot type values
    response = client.put_slot_type(
        name='photoType',
        enumerationValues=enumerationValues,
        checksum=checksum,
    )
        
    
    #================ elasticSearch - insert photo labels ====================
    from elasticsearch import Elasticsearch, RequestsHttpConnection
    from requests_aws4auth import AWS4Auth

    host = 'vpc-photos-3pl2e2gkp23t52sjzv3rove4ru.us-east-1.es.amazonaws.com' # For example, my-test-domain.us-east-1.es.amazonaws.com
    region = 'us-east-1' # e.g. us-west-1

    service = 'es'
    #credentials = boto3.Session().get_credentials()
    #print(credentials)
    awsauth = AWS4Auth('AKIA2OMBG3RF7CNI3CQS', 'omAp0iAinwmBPyiYh8yByqE0FW/0hIw3hil92D4n', region, service, session_token=None)

    es = Elasticsearch(
        hosts = [{'host': host, 'port': 443}],
        http_auth = awsauth,
        use_ssl = True,
        verify_certs = True,
        connection_class = RequestsHttpConnection
    )
    document = {}
    document['objectKey'] = name
    document['bucket'] = 'hw3-photo-bucket'

    from datetime import datetime
    now = datetime.now()
    timestamp = datetime.timestamp(now)
    document['timestamp'] = timestamp
    document['labels'] = labels
    es.index(index="photos", doc_type="Photo",body=document)


    res = es.search(index="photos", doc_type="Photo", body={"query": {"match":{"bucket": 'hw3-photo-bucket'}}})
    print('---')
    print(res)
    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }
