
# Wedding Invitation System

A web application for managing wedding guests, generating personalized PDF invitations with QR codes, and recording attendance during a wedding.

## Features

- Admin login
- Guest registration using names and phone numbers
- Guest list management, including editing and deleting guests
- Personalized PDF wedding invitations
- Unique QR codes for guests
- WhatsApp invitation sharing
- QR code scanning for guest check-in
- Attendance dashboard

## Technologies Used

- Python
- Flask
- SQLite
- HTML and CSS
- ReportLab for PDF generation
- QR code generation library

## Installation

1. Clone this repository.
2. Open the project folder in VS Code.
3. Create a virtual environment:

   python -m venv .venv

4. Activate it on Windows:

   .venv\Scripts\Activate.ps1

5. Install the required packages:

   pip install -r requirements.txt

6. Create your local `.env` file using `.env.example` as a template.
7. Start the application:

   python app.py

8. Open <http://127.0.0.1:5000> in your browser.

## Using a phone for check-in

Open the app's `/scanner` page on the phone that will be used at the entrance and sign in. The phone and computer must be able to reach the same app and database. For QR scanning, open the page over HTTPS and allow camera access when the browser prompts; mobile browsers block camera access on ordinary HTTP network addresses. If the site is only running on a computer on your Wi-Fi, publish it through a trusted HTTPS host or HTTPS reverse proxy before opening it on the phone. The guest search and manual check-in remain available if camera access is unavailable.

## Security

Never upload your `.env` file, private credentials, or live wedding guest database to GitHub.

## Project Status

Under development.
