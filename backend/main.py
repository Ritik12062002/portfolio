from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, EmailStr
from fastapi.middleware.cors import CORSMiddleware
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from fastapi import Request
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# Middleware to log all requests
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Incoming request: {request.method} {request.url}")
    logger.info(f"Origin: {request.headers.get('origin')}")
    response = await call_next(request)
    logger.info(f"Response status: {response.status_code}")
    return response

# CORS configuration
frontend_url = os.getenv("FRONTEND_URL", "")

origins = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:5175",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
    "http://127.0.0.1:5175",
]

if frontend_url:
    origins.append(frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ContactForm(BaseModel):
    name: str
    email: EmailStr
    message: str

def send_email_background(form: ContactForm, sender_email: str, sender_password: str, receiver_email: str):
    try:
        msg = MIMEMultipart()
        msg['From'] = f"Portfolio Contact Form <{sender_email}>"
        msg['To'] = receiver_email
        msg['Reply-To'] = form.email
        msg['Subject'] = f"New Contact: {form.name}"
 
        body = f"""
New Contact Request
------------------
Name: {form.name}
Email: {form.email}

Message:
{form.message}
------------------
Sent from your Portfolio Website
        """
        msg.attach(MIMEText(body, 'plain'))

        # Connect to Gmail SMTP
        logger.info(f"Connecting to SMTP server at smtp.gmail.com:587")
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.set_debuglevel(1)  # Enable debug output for SMTP
        server.starttls()
        server.login(sender_email, sender_password)
        refused = server.sendmail(sender_email, receiver_email, msg.as_string())
        if refused:
            logger.error(f"Email delivery refused by SMTP server for: {refused}")
        else:
            logger.info(f"SMTP server accepted the message for {receiver_email}")
        server.quit()
        logger.info(f"Background email successfully sent to {receiver_email}")
    except Exception as e:
        logger.error(f"Failed to send background email: {str(e)}")

@app.post("/contact")
async def send_contact_email(form: ContactForm, background_tasks: BackgroundTasks):
    logger.info(f"Received contact form submission from: {form.name}")
    
    sender_email = os.getenv("SENDER_EMAIL")
    sender_password = os.getenv("SENDER_PASSWORD")
    receiver_email = os.getenv("RECEIVER_EMAIL", "ritikkumar0987@gmail.com")

    logger.info(f"Attempting to send email via {sender_email} to {receiver_email}")

    if not sender_email or not sender_password:
            logger.error("Email credentials missing in .env file")
            raise HTTPException(status_code=500, detail="Server misconfiguration: Email credentials missing")

    # Queue the email task to run in the background
    background_tasks.add_task(send_email_background, form, sender_email, sender_password, receiver_email)
    
    return {"message": "Message sent successfully!"}

@app.get("/")
async def root():
    return {"message": "DevOps Portfolio Backend is running!"}
