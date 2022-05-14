from typing import TypedDict
from models.quiz import Question


class QuizResponseVO(TypedDict):
  quizId: str
  answers: list[Question]
  score: int

class QuizVO(TypedDict):
  guid: str
  quizId: str
  quizType: str
  questions: list[Question]