import logging
import json
import traceback
from aws_lambda_typing import context as context_, events, responses
from clients.ddb import DdbClient
from clients.auth import AuthClient
from clients.helpers import now_ts
from models.documents import ResponseDoc, QuizDoc
from models.http import HttpFailure, HttpSuccess, SubmitRequest
from models.jwt import JWT
from models.quiz import Question
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

    if event.get('body') is None:
      m = 'Invalid request, missing body'
      return HttpFailure(400, m)

    decoded: JWT = auth.decode_jwt(token)
    if not decoded or not decoded.get('data'):
      m = 'Invalid request, JWT invalid'
      return HttpFailure(400, m)
    if now_ts() > decoded['data']['expires']:
      m = 'Invalid request, JWT expired'
      return HttpFailure(400, m)

    request: SubmitRequest = json.loads(event['body'])
    quiz_doc: QuizDoc = ddb.get_quiz(request['quizType'], request['quizId'])
    if quiz_doc is None:
      m = f"Invalid request, no quiz found quizType={request['quizType']} quizId={request['quizId']}"
      return HttpFailure(400, m)

    quiz_vo: QuizVO = {}
    quiz_vo['guid'] = quiz_doc['guid']
    quiz_vo['quizType'] = quiz_doc['quizType']
    quiz_vo['quizId'] = quiz_doc['quizId']
    quiz_vo['ts'] = int(quiz_doc['ts'])
    quiz_vo['questions'] = json.loads(quiz_doc['questions'])
    
    answer_key = {}
    score = 0
    for q in quiz_vo['questions']:
      # todo: handle different answerkeys (spotifyId) TrackScoreService, FestyScoreService
      answer_key[q['id']] = q['answer']['spotifyId']
    for q in request['answers']:
      if q['answer']['spotifyId'] == answer_key[q['id']]:
        score += 1

    response_doc: ResponseDoc = {}
    response_doc['spotifyId'] = decoded['data']['spotifyId']
    response_doc['quizId'] = quiz_doc['guid']
    response_doc['quizType'] = request['quizType']
    response_doc['answers'] = json.dumps(request['answers'])
    response_doc['score'] = score
    ddb.put_quiz_response(response_doc)

    response_vo: QuizResponseVO = {}
    response_vo['quizId'] = quiz_vo['guid']
    response_vo['answers'] = request['answers']
    response_vo['score'] = score

    token = auth.sign_jwt({
      'spotifyId': decoded['data']['spotifyId'],
      'expires': now_ts() + 1000 * 60 * 60 * 8,
    })

    return HttpSuccess(json.dumps({
      'message': f'Get quiz success',
      'quiz': quiz_vo,
      'quizResponse': response_vo,
    }))

  except Exception:
    tb = traceback.format_exc()
    logger.error(tb)
    logger.error('handler failed')
    return HttpFailure(500, tb)