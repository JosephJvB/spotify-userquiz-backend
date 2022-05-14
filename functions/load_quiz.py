import logging
import json
import traceback
from aws_lambda_typing import context as context_, events, responses
from clients.ddb import DdbClient
from clients.auth import AuthClient
from clients.helpers import now_ts
from models.documents import ResponseDoc, QuizDoc
from models.http import HttpFailure, HttpSuccess
from models.view_objects import QuizResponseVO, QuizVO

logger = logging.getLogger()
logger.setLevel(logging.INFO)
ddb = DdbClient()
auth = AuthClient()

def handler(event: events.APIGatewayProxyEventV1, context: context_.Context)-> responses.APIGatewayProxyResponseV1:
  try:
    logger.info('method ' + event['httpMethod'])
    if event['httpMethod'] == 'OPTIONS':
      return HttpSuccess()

    token = (event['headers'].get('Authorization') or '').replace('Bearer ', '')
    if token is None:
      m = 'Invalid request, missing Authorization'
      return HttpFailure(400, m)

    if event.get('pathParameters') is None:
      m = 'Invalid request, missing pathParameters'
      logger.warn(m)
      return HttpFailure(400, m)
    quiz_type = event['pathParameters'].get('type')
    if quiz_type is None:
      m = 'Invalid request, missing type from pathParameters'
      logger.warn(m)
      return HttpFailure(400, m)

    decoded = auth.decode_jwt(token)
    if not decoded or not decoded.get('data'):
      m = 'Invalid request, JWT invalid'
      return HttpFailure(400, m)
    if now_ts() > decoded['data']['expires']:
      m = 'Invalid request, JWT expired'
      return HttpFailure(400, m)

    quiz_id = 'current'
    if event.get('queryStringParameters') and event.get('queryStringParameters').get('id'):
      quiz_id = event.get('queryStringParameters').get('id')

    quiz_vo: QuizVO = None
    response_vo: QuizResponseVO = None

    quiz_doc: QuizDoc = ddb.get_quiz(quiz_type, quiz_id)
    if quiz_doc is not None:
      quiz_vo: QuizVO = {}
      quiz_vo['guid'] = quiz_doc['guid']
      quiz_vo['quizType'] = quiz_doc['quizType']
      quiz_vo['quizId'] = quiz_doc['quizId']
      quiz_vo['ts'] = quiz_doc['ts']
      quiz_vo['questions'] = json.loads(quiz_doc['questions'])

      response_doc: ResponseDoc = ddb.get_quiz_response(decoded['data']['spotifyId'], quiz_vo['guid'])
      if response_doc is not None:
        response_vo['quizId'] = quiz_vo['guid']
        response_vo['score'] = response_doc['score']
        response_vo['answers'] = json.loads(response_doc['answers'])

    token = auth.sign_jwt({
      'spotifyId': decoded['data']['spotifyId'],
      'expires': now_ts() + 1000 * 60 * 60 * 8,
    })

    return HttpSuccess(json.dumps({
      'message': f'Get quiz success',
      'token': token,
      'quiz': quiz_vo,
      'quizResponse': response_vo,
    }))

  except Exception:
    tb = traceback.format_exc()
    logger.error(tb)
    logger.error('handler failed')
    return HttpFailure(500, tb)