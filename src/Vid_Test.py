import tkinter as tk
import cv2
from PIL import Image, ImageTk
from tkinter import filedialog
import shutil
import os


class VideoPlayerGUI():
    def __init__(self):
        # Create the root window
        self.window = tk.Tk()
        self.window.title("Video Player")
        self.window.geometry("400x400")

        # Define a frame to contain the label, text box, and button
        self.file_frame = tk.Frame(self.window)
        self.file_frame.pack()

        # Define the label and text box for the filename
        self.lbl_file = tk.Label(
            self.file_frame, text="Enter the video file name:")
        self.lbl_file.pack(side=tk.LEFT)

        self.txt_file = tk.Entry(self.file_frame, width=30)
        self.txt_file.pack(side=tk.LEFT)

        # Define the browse button
        self.btn_browse = tk.Button(
            self.file_frame, text="Browse", command=self.browse_file)
        self.btn_browse.pack(side=tk.LEFT)

        # Define the video player frame
        self.video_frame = tk.Frame(self.window, width=200, height=200)
        self.video_frame.pack()

        # Define the label for the video player
        self.video_label = tk.Label(self.video_frame)
        self.video_label.pack()

        # create the test button
        self.test_button = tk.Button(
            self.window, text="Test", command=self.run_test)
        self.test_button.pack(side=tk.BOTTOM)

        # Start the main loop
        self.window.mainloop()

    def browse_file(self):
        file_path = filedialog.askopenfilename()
        self.txt_file.delete(0, tk.END)
        self.txt_file.insert(0, file_path)
        new_path = r"C:\Users\Tanmay\Documents\Major_Pjct\DFSpot-Deepfake-Recognition\op\ffpp"
        shutil.copy(file_path, new_path)
        self.play_video()

    def play_video(self):
        video_path = self.txt_file.get()
        cap = cv2.VideoCapture(video_path)
        while cap.isOpened():
            ret, frame = cap.read()
            if ret:
                frame = cv2.resize(frame, (200, 200))
                img = ImageTk.PhotoImage(image=Image.fromarray(frame))
                self.video_label.config(image=img)
                self.video_label.image = img
                self.video_frame.update()
            else:
                break
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        cap.release()
        cv2.destroyAllWindows()

    def run_test(self):
        os.system('cmd/c python C:/Users/Tanmay/Documents/Major_Pjct/DFSpot-Deepfake-Recognition/src/spot_deepfakes.py \
                  --media_type video --data_dir ../op/ffpp/ --dataset ffpp --model TimmV2 TimmV2ST \
                        --model_dir ../models/ --video_id 0 --annotate True --device 0 --output_dir output/')

        os.system(r'cmd/c python C:\Users\Tanmay\Documents\Major_Pjct\DFSpot-Deepfake-Recognition\src\Vid_Result_Win.py')


VideoPlayerGUI()
