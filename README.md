# Flask Warbler
Twitter clone built in Flask Python where users can make posts, follow other users, and like posts.  
This project is a HTML serving backend server, built with Flask Python and Jinja HTML Templating. The database is managed with PostgreSQL and interacts with ORM SQLAlchemy. Tests are written with Python unittest and packages are managed with pip.

## Live Demo here: https://flask-warbler-bt2x.onrender.com/
![Flask Warbler homepage](./static/warbler-homepage.png "Flask Warbler")

## To run on your local machine:

1. Clone the repo 
```
    git clone https://github.com/clchen-arcadia/flask-warbler.git 
    cd flask-warbler/ 
```
3. Create and activate a virtual enviornment with: 
```
    python3 -m venv venv 
    source venv/bin/activate 
```
4. Then install dependencies with pip3: 
```
    pip3 install -r requirements.txt 
```
5. Then create the local database with PostgreSQL and then seed the database:
```
    psql
    =# CREATE DATABASE warbler;
    =# (control-d)
    python3 seed.py
```
6. Then create a .env file in the root directory of the project and include:
```
    SECRET_KEY=abc123
    DATABASE_URL=postgresql:///warbler
```
7. Now you can run the Flask local host 
```
    flask run 
```
Or on Macs: 
```
    flask run -p 5001 
```
And then you can visit the site on your browser at localhost:5000 or localhost:5001 
