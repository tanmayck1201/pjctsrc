import tkinter as tk
import cv2
import os
import pandas as pd


class VideoPlayer:
    def __init__(self, folder_path, csv_path):
        self.video_files = [f for f in os.listdir(
            folder_path) if f.endswith(('.mp4', '.avi', '.mkv'))]
        if not self.video_files:
            raise ValueError("No video files found in the given folder.")
        self.most_recent_video = max(
            [os.path.join(folder_path, f) for f in self.video_files], key=os.path.getctime)
        self.cap = cv2.VideoCapture(self.most_recent_video)
        self.width = 200
        self.height = 200
        self.root = tk.Tk()
        self.root.title("Video Player")
        self.root.geometry("400x450")

        # add label for CSV data
        self.csv_path = csv_path
        self.csv_data = self.get_csv_data()
        self.csv_label = tk.Label(
            self.root, text=self.csv_data, font=("Arial", 20))
        self.csv_label.pack(pady=10)

        self.canvas = tk.Canvas(
            self.root, width=self.width, height=self.height)
        self.canvas.pack()
        self.photo = None  # initialize the PhotoImage object
        self.play()

    def play(self):
        ret, frame = self.cap.read()
        if ret:
            frame = cv2.resize(frame, (self.width, self.height))
            try:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            except cv2.error:
                pass  # do nothing if color conversion fails
            if self.photo is None:  # create PhotoImage object if it doesn't exist
                self.photo = self.get_photo(frame)
                self.canvas.create_image(0, 0, image=self.photo, anchor=tk.NW)
            else:
                # update the PhotoImage data
                self.photo.config(data=self.get_photo_data(frame))
        else:
            self.cap.release()
            self.photo = self.get_photo(cv2.imread(self.most_recent_video))
            self.canvas.create_image(0, 0, image=self.photo, anchor=tk.NW)
            return
        self.root.after(30, self.play)

    def get_photo(self, frame):
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return tk.PhotoImage(data=self.get_photo_data(frame))

    def get_photo_data(self, frame):
        return cv2.imencode('.png', frame)[1].tobytes()

    def run(self):
        self.root.mainloop()

    def get_csv_data(self):
        try:
            df = pd.read_csv(self.csv_path)
            last_row = df.iloc[-1]
            last_col_data = last_row.iloc[-1]
            return f"The uploaded video is: {last_col_data}"
        except Exception as e:
            return f"Error: {str(e)}"


if __name__ == "__main__":
    player = VideoPlayer("C:/Users/Tanmay/Documents/Major_Pjct/DFSpot-Deepfake-Recognition/src/output",
                         "C:/Users/Tanmay/Documents/Major_Pjct/DFSpot-Deepfake-Recognition/src/output/predictions.csv")
    player.run()
