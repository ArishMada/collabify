from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy.orm import Session
import crud, models, schemas
from database import engine, get_db
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import EmailStr
from fastapi import Depends
from datetime import timedelta
from fastapi.middleware.cors import CORSMiddleware
from jose import JWTError, jwt

models.Base.metadata.create_all(bind = engine)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
SECRET_KEY = "asecretkeysisasecretkeysothisisasecret"
ALGORITHM = "HS256"

collabify = FastAPI()

origins = {
    "*"
}

collabify.add_middleware(
   CORSMiddleware,
    allow_origins = origins,
    allow_credentials =True,
    allow_methods = ["*"],
    allow_headers= ["*"],
)

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms = ALGORITHM)
        email: EmailStr = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = schemas.TokenData(email = email)
    except JWTError:
        raise credentials_exception
    
    return token_data
        
@collabify.get("/")
def index():
    return {"Collabify" : "Productive App to Help Your Study"}

@collabify.post("/signup/", response_model = schemas.Users)
async def signup(
    payload: schemas.CreateUserSchema,
    session: Session = Depends(get_db),
):
    db_user = crud.get_user_by_email(session, email = payload.email)
    if db_user:
        raise HTTPException(status_code = 400, detail = "Email already registered")
    # bytePwd = payload.password.encode('utf-8')
    # mySalt = bcrypt.gensalt()
    # hashed_pass = bcrypt.hashpw(bytePwd, mySalt)
    hashed_pass = crud.pwd_context.hash(payload.password)
    return crud.create_user(session, email = payload.email, password = hashed_pass)

@collabify.post("/token", response_model = schemas.Token)
async def login(
    payload: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_db),
):
    db_user = crud.get_user_by_email(session, email = payload.username)
    if not db_user:
        raise HTTPException(status_code = 400, detail = "Email does not exists")
    check_user = crud.auth_user(session, payload.username, payload.password)
    if not check_user:
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail = "Incorrect username or password",
            headers = {"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes = 30)
    access_token = crud.create_token(
        data={"sub": check_user.email}, expires_delta = access_token_expires
    )
    crud.user_active(session, email = payload.username)
    return {"access_token": access_token, "token_type": "bearer"}

@collabify.get("/logout")
def user_logout(
    token_data: schemas.TokenData = Depends(get_current_user),
    session: Session = Depends(get_db)
):
    crud.user_inactive(session, token_data.email)
    return {"Message": "Successfully Logout"}

@collabify.delete("/delete-user/{user_id}", response_model = schemas.UserSchema)
def delete_user(
    id: int,
    token: str = Depends(oauth2_scheme),
    session: Session = Depends(get_db)
):
    return crud.delete_user(session, id)

@collabify.get("/protected_route")
async def protected_route(
    token_data: schemas.TokenData = Depends(get_current_user)
):
    return {"Message": "Access granted"}