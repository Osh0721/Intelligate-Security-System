import cv2 as cv
import numpy as np
import os
from mtcnn.mtcnn import MTCNN
from keras_facenet import FaceNet
import joblib
import time
import subprocess
import mysql.connector
from datetime import datetime

# Database configuration
db_config = {
    'host': '127.0.0.1:3306',
    'user': 'root',
    'password': 'Intelligate@123',
    'database': 'Intelligate'
}

# Define the path to your repository's root directory
repo_path = '/home/samanerendra/Edge-AI-CW'

# Ensure you're in the correct directory
os.chdir(repo_path)

# Pull the latest changes from the repository
subprocess.run(['git', 'pull'], check=True)

# Start timing the entire script execution
script_start_time = time.time()

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
embedder = FaceNet()
model = joblib.load('trained_model/face_recognition_model.pkl')
encoder = joblib.load('trained_model/label_encoder.pkl')
detector = MTCNN()

def get_embedding(face_img):
    face_img = face_img.astype('float32')
    face_img = np.expand_dims(face_img, axis=0)
    embedding = embedder.embeddings(face_img)
    return embedding[0]

def get_frames_from_video(video_path, samples=5):
    cap = cv.VideoCapture(video_path)
    total_frames = int(cap.get(cv.CAP_PROP_FRAME_COUNT))
    frame_rate = cap.get(cv.CAP_PROP_FPS)
    frames_to_sample = np.linspace(0, total_frames-1, samples, endpoint=False).astype(int)
    sampled_frames = []

    for i in frames_to_sample:
        cap.set(cv.CAP_PROP_POS_FRAMES, i)
        ret, frame = cap.read()
        if ret:
            rgb_img = cv.cvtColor(frame, cv.COLOR_BGR2RGB)
            faces = detector.detect_faces(rgb_img)
            for face in faces:
                x, y, w, h = face['box']
                face_img = rgb_img[y:y+h, x:x+w]
                if face_img.size > 0:
                    sampled_frames.append(cv.resize(face_img, (160, 160)))
    cap.release()
    return sampled_frames

def insert_into_db(name, date, in_time):
    # Connect to the database
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    try:
        sql = "INSERT INTO your_table_name (Name, Date, `IN-Time`) VALUES (%s, %s, %s)"
        val = (name, date, in_time)
        cursor.execute(sql, val)
        conn.commit()
        print(f"Record inserted for {name} at {in_time} on {date}")
    except mysql.connector.Error as err:
        print(f"Failed to insert record: {err}")
    finally:
        cursor.close()
        conn.close()

def predict_person_from_samples(frames):
    best_prediction = ("Unknown", 0.5)  # (Name, confidence)
    for face in frames:
        if face is not None:
            embedding = get_embedding(face)
            embedding = np.expand_dims(embedding, axis=0)
            prediction = model.predict(embedding)
            confidence = model.predict_proba(embedding).max()
            if confidence > best_prediction[1]:  # Confidence threshold
                person_name = encoder.inverse_transform(prediction)[0]
                best_prediction = (person_name, confidence)
                
                # Get current date and time
                now = datetime.now()
                date = now.strftime('%Y-%m-%d')
                in_time = now.strftime('%H:%M:%S')
                
                # Print the prediction along with date and time
                if person_name != "Unknown":
                    print(f"Predicted person: {person_name} at {in_time} on {date}")
                    insert_into_db(person_name, date, in_time)
    return best_prediction[0]


# Main script execution begins here
# Specify the path to your existing video file here
video_path = "video_clip/captured_video.mp4"

# Process the video and predict person
sampled_frames = get_frames_from_video(video_path, 5)
person = predict_person_from_samples(sampled_frames)

# Print the predicted person
print(f"Predicted person: {person}")

# End timing the entire script execution
script_end_time = time.time()

# Calculate and print the total duration
total_duration = script_end_time - script_start_time
print(f"Total script execution took {total_duration:.2f} seconds.")
