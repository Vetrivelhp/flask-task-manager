from flask import Flask, request, render_template, url_for, redirect, session
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, update, event
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.engine import Engine
from datetime import datetime
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHash    
from contextlib import contextmanager
import re
import os
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///task_manager.db")

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace(
        "postgres://",
        "postgresql://",
        1
    )

if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
else:
    engine = create_engine(
        DATABASE_URL,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True
    )

Base = declarative_base()



#User Table --to store user details

class User(Base):
    __tablename__ = "users_tbl"

    id = Column(Integer, primary_key=True)
    user_name = Column(String(150), unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

#TaskGroups Table --to store task list and user_id

class TaskGroups(Base):
    __tablename__ = "task_groups_tbl"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users_tbl.id"), nullable=False)
    title = Column(String(400), nullable=False)
    description = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

#Categories Table  --to store categories details

class Categories(Base):
    __tablename__ = "categories_tbl"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users_tbl.id"), nullable=False)
    name = Column(String(100), nullable=False)

#Tasks Table --to store task details

class Tasks(Base):
    __tablename__ = "tasks_tbl"

    id = Column(Integer, primary_key=True)
    group_id = Column(
        Integer,
        ForeignKey("task_groups_tbl.id", ondelete="CASCADE"),
        nullable=False
    )

    parent_task_id = Column(
        Integer,
        ForeignKey("tasks_tbl.id"),
        nullable=True
    )
    order_index = Column(Integer, nullable=False, default=0)
    title = Column(String(255), nullable=False)
    state = Column(Integer, default=0)  # 0=pending, 1=done, 2=ongoing
    due_date = Column(DateTime, nullable=True)
    priority = Column(Integer, default=1)  # 1=low, 2=medium, 3=high
    category_id = Column(Integer, ForeignKey("categories_tbl.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


if DATABASE_URL.startswith("sqlite"):
    @event.listens_for(Engine, "connect")
    def enable_sqlite_fk(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


#Create Table

Base.metadata.create_all(engine)

SessionLocal = sessionmaker(
    bind=engine,
    expire_on_commit=False
)


@contextmanager
def get_db():
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except:
        db.rollback()
        raise
    finally:
        db.close()


app.secret_key = os.environ.get("SECRET_KEY")

#Customize Password Hasher

ph = PasswordHasher(
    time_cost = 3,
    memory_cost = 10 * 1024,
    parallelism = 2,
    hash_len = 32,
    salt_len = 16
)

#Create User and store user details

@app.route('/', methods=['GET', 'POST'])
def home():
    with get_db() as db:
        if request.method == 'POST':
            username = request.form['user']
            pass1 = request.form['pass1']
            pass2 = request.form['pass2']
            
            if pass1 != pass2:
                return "Passwords Do Not Match", 400
                
            pattern = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&]).{8,}$'

            if not re.match(pattern, pass2):
                return "Weak password", 400

            log_check = db.query(User).filter(
                User.user_name == username
            ).first()

            if log_check:
                return "Username already exist", 400
                
            hashed_password = ph.hash(pass1)
            
            new_user = User(
                user_name = username,
                hashed_password = hashed_password
            )
            
            db.add(new_user)
            
            return redirect(url_for('login'))

    return render_template('sign.html')

#Login User and verify with database

@app.route('/login', methods = ['GET','POST'])
def login():
    with get_db() as db:
        if request.method == 'POST':
            log_user = request.form['user']
            log_psd = request.form['pass']
            
            log_check = db.query(User).filter(
                User.user_name == log_user
            ).first()

            try:
                if not log_check:
                    raise VerifyMismatchError
                ph.verify(log_check.hashed_password,log_psd)
                session["user_id"] = log_check.id
                return redirect(url_for('task_dashboard'))
                    
            except VerifyMismatchError:
                return "Wrong Username or Password", 401
                    
            except InvalidHash:
                return "Authentication System Error", 500   
        
    return render_template('login.html')



@app.route('/task_dashboard', methods = ['GET','POST'])
def task_dashboard():
    with get_db() as db:        
        user_id = session.get("user_id")
        if not user_id:
            return "Not Logged In!!!", 401

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            session.clear()
            return "Not Logged In!!!", 401
       
    return render_template('task_dashboard.html', username=user.user_name)

@app.route('/api/create_task', methods = ['POST'])
def create_task():
    with get_db() as db:
        user_id = session.get("user_id")
        if not user_id:
            return "Not Logged In!!!", 401
            
        data = request.json
        client_map = {}
        if not data["task_list"]:
            return "Cannot create empty task"
          
        task_group = TaskGroups(
            title = data["title"],
            description = data["description"],
            user_id = user_id
        )
                
        db.add(task_group)
        db.flush()  # get id without committing

        tasks = []
        for task_data in data["task_list"]:
            task = Tasks(
                group_id=task_group.id,
                title=task_data["title"],
                state=task_data["state"],
                order_index=task_data["order_index"]
            )
            tasks.append(task)
            client_map[task_data["client_id"]] = task
        db.add_all(tasks)
        db.flush()
            
        for task_data in data["task_list"]:
            parent_client = task_data.get("parent_client_id")
            if parent_client:
                parent_task = client_map.get(parent_client)
                current_task = client_map.get(task_data["client_id"])

                if parent_task and current_task:
                    current_task.parent_task_id = parent_task.id
                    
    return {
        "success": True,
        "id": task_group.id,
        "title": task_group.title,
        "description": task_group.description or "",
        "created_at": task_group.created_at.strftime("%d %b %Y, %I:%M %p")
    }
    
@app.route('/api/tasks/<int:id>', methods = ['GET'])
def send_tasks(id):
    with get_db() as db:
        user_id = session.get("user_id")
        if not user_id:
            return "Not Logged In!!!", 401
            
        groups = db.query(TaskGroups).filter(
            TaskGroups.id == id,
            TaskGroups.user_id == user_id
        ).first()
        
        if not groups:
            return {"error": "Not found"}, 404
            
        tasks = db.query(Tasks).filter(
            Tasks.group_id == id
        ).order_by(Tasks.order_index.asc()).all()

    return[{
        "id": t.id,
        "title": t.title,
        "state": t.state,
        "parent_id": t.parent_task_id
    } for t in tasks]
    
@app.route('/api/edit/<int:id>', methods = ['PATCH'])
def edit_tasks(id):
    with get_db() as db:
        user_id = session.get("user_id")
        if not user_id:
            return "Not Logged In!!!", 401
            
        data = request.json
       
        group = db.query(TaskGroups).filter(
            TaskGroups.id == id,
            TaskGroups.user_id == user_id
        ).first()
            
        if not group:
            return {"error": "Group not found"}, 404
            
        if not data["task_list"]:
            db.delete(group)
                
            return {"deleted": True}    
            
        group.title = data["title"]
        group.description = data["description"]
            
        existing_tasks = db.query(Tasks).filter(
            Tasks.group_id == id
        ).all()

        existing_task_map = {t.id: t for t in existing_tasks}
        incoming_ids = set()  

        client_map = {}
        tasks = []
        for task_data in data["task_list"]:
            task_id = task_data.get("id")

            if task_id and int(task_id) in existing_task_map:
                task = existing_task_map[int(task_id)]
                task.title = task_data["title"]
                task.state = task_data["state"]
                task.order_index = task_data["order_index"]
                incoming_ids.add(int(task_id))

                client_map[task_data["client_id"]] = task

            else:
                task = Tasks(
                    group_id=group.id,
                    title=task_data["title"],
                    state=task_data["state"],
                    order_index=task_data["order_index"]
                )
                tasks.append(task)
                client_map[task_data["client_id"]] = task
        db.add_all(tasks)
        db.flush()
                    
        for task_data in data["task_list"]:
            current_task = client_map.get(task_data["client_id"])
            # Always reset
            current_task.parent_task_id = None
            parent_client = task_data.get("parent_client_id")
            if parent_client:
                parent_task = client_map.get(parent_client)
                if parent_task:
                    current_task.parent_task_id = parent_task.id

            # DELETE removed tasks
        for existing_id in existing_task_map:
            if existing_id not in incoming_ids:
                db.delete(existing_task_map[existing_id])
            
        print("Editing group:", id)

    return {
        "success": True,
        "id": group.id,
        "title": group.title,
        "description": group.description or ""
    }
    
@app.route('/api/delete/<int:id>', methods=['DELETE'])
def delete_task(id):
    with get_db() as db:
        user_id = session.get("user_id")
        if not user_id:
            return "Not Logged In!!!", 401
            
        group = db.query(TaskGroups).filter(
            TaskGroups.id == id,
            TaskGroups.user_id == user_id
        ).first()
            
        if not group:
            return {"error": "Group not found"}, 404
            
        db.delete(group)

    return {"Deleted": True}
    

@app.route('/api/groups')
def get_groups():
    with get_db() as db:
        user_id = session.get("user_id")
        if not user_id:
            return "Not Logged In!!!", 401
            
        groups = db.query(TaskGroups).filter(
            TaskGroups.user_id == user_id
        ).order_by(TaskGroups.created_at.desc()).all()

    return[{
        "id": g.id,
        "title": g.title,
        "description": g.description,
        "created_at": g.created_at.strftime("%d %b %Y, %I:%M %p")
    } for g in groups]


@app.route("/logout")
def logout():
    session.clear()
    return {"success": True}

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000))
    )
