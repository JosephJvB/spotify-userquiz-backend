import boto3
from boto3.dynamodb.types import TypeDeserializer, TypeSerializer
from boto3_type_annotations.dynamodb import Client

from models.documents import QuizDoc, ResponseDoc

class DdbClient():
  client: Client
  td: TypeDeserializer
  ts: TypeSerializer
  def __init__(self):
    self.client = boto3.client('dynamodb')
    self.td = TypeDeserializer()
    self.ts = TypeSerializer()
  
  def get_quiz(self, quizType: str, quizId: str):
    r = self.client.get_item(
      TableName='SpotifyQuiz',
      Key={
        'quizType': { 'S': quizType },
        'quizId': { 'S': quizId },
      }
    )
    return self.to_object(r.get('Item'))

  def query_quizzes(self, quizType: str) -> list[QuizDoc]:
    r = self.client.query(
      TableName='SpotifyQuiz',
      KeyConditionExpression='#quizType = :quizType',
      ExpressionAttributeNames={ '#quizType': 'quizType' },
      ExpressionAttributeValues={ ':quizType': { 'S': quizType } },
    )
    items: list[dict] = r['Items']
    while r.get('LastEvaluatedKey'):
      r = self.client.query(
        TableName='SpotifyQuiz',
        ExclusiveStartKey=r['LastEvaluatedKey'],
        KeyConditionExpression='n_quizType = v_quizType',
        ExpressionAttributeNames={ 'n_quizType': 'quizType' },
        ExpressionAttributeValues={ 'v_quizType': { 'S': quizType } },
      )
      items.extend(r['Items'])
    return [self.to_object(i) for i in items]

  def get_quiz_response(self, spotifyId: str, quizId: str) -> list[QuizDoc]:
    r = self.client.get_item(
      TableName='SpotifyQuizResponse',
      Key={
        'spotifyId': { 'S': spotifyId },
        'quizId': { 'S': quizId },
      }
    )
    return self.to_object(r.get('Item'))

  def put_quiz_response(self, response: ResponseDoc) -> list[QuizDoc]:
    r = self.client.put_item(
      TableName='SpotifyQuizResponse',
      Item=self.to_document(response)
    )

  def to_document(self, obj: dict):
    return {
      k: self.ts.serialize(v) for k, v in obj.items()
    }
  def to_object(self, item: dict):
    if not item:
      return None
    return {
      k: self.td.deserialize(item[k]) for k in item.keys()
    }