import json
import boto3

import sys
sys.path.insert(1,'/home/ubuntu/build/python/lib/python3.6/site-packages')
from elasticsearch import Elasticsearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth



# configurations
region = 'us-east-1'
lex_client = boto3.client('lex-runtime', region_name=region)

host = 'vpc-photos-3pl2e2gkp23t52sjzv3rove4ru.us-east-1.es.amazonaws.com'
service = 'es'
awsauth = AWS4Auth('AKIA2OMBG3RF4SDW56EH','EEwiCkqr/uHDcz+rxf8nLG3nHBNOZe/9AuvAOUxJ',region,service,session_token=None)

es = Elasticsearch(
        hosts = [{'host': host, 'port': 443}],
        http_auth = awsauth,
        use_ssl = True,
        verify_certs = True,
        connection_class = RequestsHttpConnection
    )

# res = es.search(index='restaurants', doc_type='Restaurant', body={"query": {"match":{"cuisine": Cuisine}}})

######################################################
#     lex utils
######################################################

######################################################


def lambda_handler(event, context):
    # print(event)
    body = json.loads(event['body'])
    print(body)
    query = body['message']
    #query = "bus"
    
    only_keyword = query.split()
    if len(only_keyword) != 1:
        # Send message to Lex
        response_lex = lex_client.post_text(
            botName='photoSearch',                 
            botAlias='test',
            userId="test",           
            inputText=query
        )
        print("lex-response: ", response_lex)
        
        # Extract keywords detected by Lex
        keywords = []
        if 'slots' not in response_lex:
            print("Query has no results")
        else:
            print ("slots received: ",response_lex['slots'])
            slot_val = response_lex['slots']
            for key,value in slot_val.items():
                if value!=None:
                    keywords.append(value)
    else:
        keywords = only_keyword
        
    print('keywords for query: ',keywords)
        
    # extend keywords with some singular nouns
    keywords_singular = []
    for keyword in keywords:
        if keyword[-2:] == 'es':
            keywords_singular.append(keyword[:-2])
            keywords_singular.append(keyword[:-1])
        elif keyword[-1] == 's':
            keywords_singular.append(keyword[:-1])
    keywords = keywords + keywords_singular
    print('keywords for query (add singular): ',keywords) 

    # es query
    print("\n es query process: ")
    img_paths = []
    
    for key in keywords:
        response_es = es.search(index="photos", doc_type="Photo", body={"query": {"match":{"labels": key}}})
        #print('es response: ',response_es)
        imgs = response_es['hits']['hits']
        #print(len(imgs),imgs)
        for img in imgs:
            img_bucket = img["_source"]["bucket"]
            img_name = img["_source"]["objectKey"]
            img_link = 'https://s3.amazonaws.com/' + str(img_bucket) + '/' + str(img_name)
            if img_link not in img_paths:
                img_paths.append(img_link)
    
    
    print(img_paths,'\n')
    
    return {
        'statusCode':200,
        'body': json.dumps({
            'userQuery':query,
            'keywords': keywords,
            'imagePaths':img_paths,
        }),
        'headers': {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Credentials": True
        },
    }
