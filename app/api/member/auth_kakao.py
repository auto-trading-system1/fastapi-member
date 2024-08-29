from fastapi import Depends, APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse, JSONResponse
from app.schemas.auth_kakao import TokenRequest, TokenResponse
import requests
import logging
import jwt

from sqlalchemy.orm import Session
from app.core.db_manager import SessionLocal, engine
from app.models.auth_token_info import AuthTokenInfo


router = APIRouter()

AUTHORIZE_ENDPOINT = "https://kauth.kakao.com/oauth/authorize"
ACCESS_TOKEN_ENDPOINT = "https://kauth.kakao.com/oauth/token"
USER_INFO_ENDPOINT = "https://kapi.kakao.com/v2/user/me"


# 의존성 생성
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/run-kakao-auth")
def run_kakao_auth(user_id: str = Query(..., alias="user-id"), db: Session = Depends(get_db)):
    # 1. API Key 조회
    logging.info("GET /run-kakao-auth start")
    api_key = get_api_key(user_id, db)

    return JSONResponse({"api_key": api_key})


# 카카오 간편인증 - 인가 코드 받기
@router.get("/login")
def login(redirect_url: str = Query(..., alias="redirect-url"), api_key: str = Query(..., alias="api-key")):
    logging.info("GET /login start")

    # 카카오 인증 url로 get 요청
    try:
        ext_url = f"{AUTHORIZE_ENDPOINT}?response_type=code&client_id={api_key}&redirect_uri={redirect_url}"
        logging.info(f"request url for kakao : {ext_url}")
        response = requests.get(ext_url)

        # API 응답 성공 여부 확인
        response.raise_for_status()

        return RedirectResponse(url=ext_url)
    except requests.RequestException as e:
        logging.error(f"카카오 인증 요청에 실패하였습니다 : {e}")
        raise HTTPException(status_code=500, detail="인증 실패")


# 카카오 간편인증 - Access Token 발급받기
@router.post("/access-token",
            summary="access token 발급",
            description="카카오 OAuth2.0 access token을 발급받습니다.",
            response_description="access token 반환")
def get_access_token(token_request: TokenRequest):
    logging.info("POST /get_access_token 요청")

    try:
        response = requests.post(
            ACCESS_TOKEN_ENDPOINT,
            data=token_request.dict(exclude_none=True)
        )
        response.raise_for_status()

        token_response = response.json()

        return JSONResponse(content=token_response)

    except requests.RequestException as e:
        logging.error(f"Access Token 발급에 실패하였습니다 : {e}")
        raise HTTPException(status_code=500, detail="Access Token 발급 실패")


@router.post("/verify-id-token",
            summary="jwt 토큰 인증",
            description="jwt를 이용하여 토큰 유효성을 검증합니다.",
            response_description="인증된 토큰 정보")
def verify_id_token(id_token: str):
    try:
        # ID 토큰의 유효성을 검증합니다. 여기서 공개 키를 사용하여 서명을 검증합니다.
        decoded_token = jwt.decode(id_token, options={"verify_signature": False})
        return JSONResponse(content={"decoded_token": decoded_token})
    except jwt.PyJWTError as e:
        logging.error(f"ID 토큰 검증에 실패하였습니다 : {e}")
        raise HTTPException(status_code=400, detail="ID 토큰 검증 실패")
    


# ------------------------------------------------------------------------------------- #


# DB에서 API Key 조회
def get_api_key(user_id: str, db: Session = Depends(get_db)):
    try:
        auth_token = db.query(AuthTokenInfo).filter(AuthTokenInfo.user_id == user_id).first()
        api_key = auth_token.api_key
    except Exception as e:
        print(f"Error occurred: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    
    if auth_token is None:
        raise HTTPException(status_code=404, detail="Auth token not found")
    
    return api_key


# 인가코드 발급 요청
def get_auth_code(redirect_uri: str, api_key: str):
    logging.info("GET /authorize 요청")

    # 카카오 인증 url로 get 요청
    try:
        ext_url = f"{AUTHORIZE_ENDPOINT}?response_type=code&client_id={api_key}&redirect_uri={redirect_uri}"
        logging.info(f"request url for kakao : {ext_url}")
        response = requests.get(ext_url)

        # API 응답 성공 여부 확인
        response.raise_for_status()

        return RedirectResponse(url=ext_url)
    except requests.RequestException as e:
        logging.error(f"카카오 인증 요청에 실패하였습니다 : {e}")
        raise HTTPException(status_code=500, detail="인증 실패")



