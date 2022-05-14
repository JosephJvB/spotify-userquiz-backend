from typing import TypedDict


class JWTData(TypedDict):
  expires: int
  spotifyId: str
class JWT(TypedDict):
  data: JWTData