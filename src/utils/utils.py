from glob import glob
import os
import os.path
import fnmatch
from pprint import pprint
from typing import Iterable, List
import albumentations as A
import cv2
import numpy as np
import scipy
from sklearn import datasets
import torch
from PIL import Image
from albumentations.pytorch import ToTensorV2
from matplotlib import pyplot as plt
from torch import nn as nn
from torchvision import transforms
import itertools
from architectures import fornet
from architectures.fornet import FeatureExtractor
from blazeface import FaceExtractor, BlazeFace, VideoReader
import pandas as pd
from PIL import Image
import json
import sys
IN_COLAB = 'google.colab' in sys.modules
if(IN_COLAB):
    from tqdm import tqdm_notebook as tqdm
elif(not IN_COLAB):
    from tqdm import tqdm


formats = ['image', 'video']
models = ['TimmV2', 'TimmV2ST', 'ViT', 'ViTST']
datasets = ['ffpp', 'dfdc', 'celeb']


def get_transformer(face_policy: str, patch_size: int, net_normalizer: transforms.Normalize, train: bool):
    # Transformers and traindb
    if face_policy == 'scale':
        # The loader crops the face isotropically then scales to a square of size patch_size_load
        loading_transformations = [
            A.PadIfNeeded(min_height=patch_size, min_width=patch_size,
                          border_mode=cv2.BORDER_CONSTANT, value=0, always_apply=True),
            A.Resize(height=patch_size, width=patch_size, always_apply=True),
        ]
        if train:
            downsample_train_transformations = [
                # replaces scaled dataset
                A.Downscale(scale_max=0.5, scale_min=0.5, p=0.5),
            ]
        else:
            downsample_train_transformations = []
    elif face_policy == 'tight':
        # The loader crops the face tightly without any scaling
        loading_transformations = [
            A.LongestMaxSize(max_size=patch_size, always_apply=True),
            A.PadIfNeeded(min_height=patch_size, min_width=patch_size,
                          border_mode=cv2.BORDER_CONSTANT, value=0, always_apply=True),
        ]
        if train:
            downsample_train_transformations = [
                # replaces scaled dataset
                A.Downscale(scale_max=0.5, scale_min=0.5, p=0.5),
            ]
        else:
            downsample_train_transformations = []
    else:
        raise ValueError(
            'Unknown value for face_policy: {}'.format(face_policy))

    if train:
        aug_transformations = [
            A.Compose([
                A.HorizontalFlip(),
                A.OneOf([
                    A.RandomBrightnessContrast(),
                    A.HueSaturationValue(
                        hue_shift_limit=10, sat_shift_limit=30, val_shift_limit=20),
                ]),
                A.OneOf([
                    A.ISONoise(),
                    A.IAAAdditiveGaussianNoise(scale=(0.01 * 255, 0.03 * 255)),
                ]),
                A.Downscale(scale_min=0.7, scale_max=0.9,
                            interpolation=cv2.INTER_LINEAR),
                A.ImageCompression(quality_lower=50, quality_upper=99),
            ], )
        ]
    else:
        aug_transformations = []

    # Common final transformations
    final_transformations = [
        A.Normalize(mean=net_normalizer.mean, std=net_normalizer.std, ),
        ToTensorV2(),
    ]
    transf = A.Compose(
        loading_transformations + downsample_train_transformations + aug_transformations + final_transformations)
    return transf


def plot_confusion_matrix(cm, classes,
                          normalize=False,
                          title='Confusion matrix',
                          cmap=plt.cm.Blues):
    """
    This function prints and plots the confusion matrix.
    Normalization can be applied by setting `normalize=True`.
    """
    plt.imshow(cm, interpolation='nearest', cmap=cmap)
    plt.title(title)
    plt.colorbar()
    tick_marks = np.arange(len(classes))
    plt.xticks(tick_marks, classes, rotation=0)
    plt.yticks(tick_marks, classes)

    if normalize:
        cm = cm.astype('float') / cm.sum(axis=1)[:, np.newaxis]
        print("Normalized confusion matrix")
    else:
        print('Confusion matrix, without normalization')

    print(cm)

    thresh = cm.max() / 2.
    for i, j in itertools.product(range(cm.shape[0]), range(cm.shape[1])):
        plt.text(j, i, cm[i, j],
                 horizontalalignment="center",
                 color="white" if cm[i, j] > thresh else "black")

    plt.tight_layout()
    plt.ylabel('True label')
    plt.xlabel('Predicted label')


def get_video_paths(data_dir, num_videos):
    ext = ['mp4', 'avi', 'mkv', 'wmv']    # Add image formats here
    files = []
    for filename in os.listdir(data_dir):
        if any(filename.lower().endswith('.' + e) for e in ext):
            files.append(os.path.join(data_dir, filename))
    files.sort(reverse=False)
    #video_paths = glob(data_dir + "**/*.mp4", recursive=True)
    video_paths = files
    # video_idxs = [2,5,6,7]# [x for x in range(0,num_videos)]  # if num_videos is 3, then video_idxs = [0,1,2] i.e we will test videos at index 0,1,2 in file_names
    file_names = []
    for i in video_paths:
        file_names.append(os.path.basename(i))
    file_names.sort(reverse=False)
    # print("videos:",files)
    return file_names, video_paths


def get_model_paths(model, model_dir, dataset, choices):
    model_paths = []
    for file_name in os.listdir(model_dir):
        if file_name.endswith(".pth") and dataset in file_name:
            model_name = os.path.splitext(file_name)[0]
            model_type = model_name.split("_")[1]
            if model_type in choices and choices[model_type] in model:
                model_paths.append(os.path.join(model_dir, file_name))
    return model_paths


def get_model_paths(model, model_dir, dataset, choices):
    model_paths = []
    for root, dirs, files in os.walk(model_dir):
        for file in files:
            if file.endswith('.pth'):
                model_path = os.path.join(root, file)
                if file.startswith(dataset):
                    model_paths.append(model_path)

    print("Found the following model files in the directory:")
    print(model_paths)

    a = []
    for i in model_paths:
        if(choices[os.path.basename(i).split(".")[0].split("_")[1]] in model):
            a.append(i)
    model_paths = a
    return model_paths


def load_weights(model_paths, choices, device):
    model_list = []
    for i in tqdm(model_paths, desc="Loading Models"):
        net_name = choices[i.split("\\")[-1].split("_")[1].split(".")[0]]
        net_class = getattr(fornet, net_name)
        net: FeatureExtractor = net_class().eval().to(device)
        net.load_state_dict(torch.load(i, map_location='cpu')['net'])
        model_list.append(net)
    return model_list


def load_face_extractor(blazeface_dir, device, fpv):

    facedet = BlazeFace().to(device)
    facedet.load_weights(
        r"C:\Users\Tanmay\Documents\Major_Pjct\DFSpot-Deepfake-Recognition\src\blazeface\blazeface.pth")
    facedet.load_anchors(
        r"C:\Users\Tanmay\Documents\Major_Pjct\DFSpot-Deepfake-Recognition\src\blazeface\anchors.npy")

    videoreader = VideoReader(verbose=False)
    def video_read_fn(x): return videoreader.read_frames(
        x, num_frames=fpv)

    return FaceExtractor(video_read_fn=video_read_fn, facedet=facedet)


def extract_faces(data_dir, file_names, video_idxs, transformer, face_extractor, num_videos, fpv):
    faces = face_extractor.process_videos(
        input_dir=data_dir, filenames=file_names, video_idxs=video_idxs)

    faces_frames = [fpv*x for x in range(0, num_videos+1)]   # [0,32,64,96]

    faces_hc = torch.stack([transformer(image=frame['faces'][0])[
                           'image'] for frame in faces if len(frame['faces'])])

    return faces_hc, faces_frames


def predict(ensemble_models, data_dir, file_names, video_idxs, num_videos, faces, faces_frames, model, save_csv=True, true_class=False):
    predictions = {}
    predictions_with_frame_level_data = {}
    with torch.no_grad():
        for i in tqdm(range(0, num_videos), desc='Predicting: '):  # (0,3) i.e 0,1,2
            score, preds = ensemble_models(
                faces[faces_frames[i]:faces_frames[i+1]])
            if(not true_class):
                predictions[data_dir+file_names[video_idxs[i]]] = [score, {'ensemble_score': sum(score.values())/(len(model))}, {
                    'predicted_class': 'real' if sum(score.values())/(len(model)) < 0.3 else 'fake'}]
                predictions_with_frame_level_data[data_dir+file_names[video_idxs[i]]] = [score, preds, {'ensemble_score': sum(score.values())/(len(model))}, {
                    'predicted_class': 'real' if sum(score.values())/(len(model)) < 0.3 else 'fake'}]
            else:
                predictions[data_dir+file_names[video_idxs[i]]] = [score, {'ensemble_score': sum(score.values())/(len(model))}, {
                    'predicted_class': 'real' if sum(score.values())/(len(model)) < 0.3 else 'fake', 'true_class': input_dir.split("/")[3]}]
                predictions_with_frame_level_data[data_dir+file_names[video_idxs[i]]] = [score, preds, {'ensemble_score': sum(score.values())/(len(model))}, {
                    'predicted_class': 'real' if sum(score.values())/(len(model)) < 0.3 else 'fake', 'true_class': input_dir.split("/")[3]}]
    if(save_csv):
        pclass = []
        for preds in predictions:
            predicted_class = predictions[preds][2]['predicted_class']
            pclass.append(predicted_class)
        data = {'video_path': [x for x in predictions.keys()],
                'prediction':  pclass}
        df = pd.DataFrame(data)
        df.to_csv('predictions.csv')
        print("Predictions saved to predictions.csv")
    return predictions, predictions_with_frame_level_data


def numberWithoutRounding(num, precision=4):
    [beforeDecimal, afterDecimal] = str(num).split('.')
    return beforeDecimal + '.' + afterDecimal[0:precision]


def count_frames(path):
    video = cv2.VideoCapture(path)
    return int(video.get(cv2.CAP_PROP_FRAME_COUNT))


def fpv_list(vid_paths):
    fpv = []
    for i in vid_paths:
        fpv.append(count_frames(i))
    return fpv


def extract_predict_annotate(output_dir, ensemble_models, video_glob, video_idxs, transformer, blazeface_dir, device, model_list):

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    facedet = BlazeFace().to(device)
    facedet.load_weights(
        r"C:\Users\Tanmay\Documents\Major_Pjct\DFSpot-Deepfake-Recognition\src\blazeface\blazeface.pth")
    facedet.load_anchors(
        r"C:\Users\Tanmay\Documents\Major_Pjct\DFSpot-Deepfake-Recognition\src\blazeface\anchors.npy")
    videoreader = VideoReader(verbose=False)

    fpv = fpv_list(video_glob)

    print("FPV of the videos that are to be processed:",
          [fpv[x] for x in video_idxs if x < len(fpv)])

    _video_idxs = len(video_idxs)

    # extract faces:
    predictions = {}
    predictions_with_frame_level_data = {}
    with torch.no_grad():

        no_faces = []
        too_large = []
        iterator = tqdm(video_idxs, desc='Predicting')
        for vid in iterator:
            iterator.update()
            if vid >= len(fpv):
                continue  # skip invalid index
            if(fpv[vid] > 1000):
                too_large.append(vid)
                print(
                    f"The video with id {vid} is too large to be processed. Hence, skipping it. Trim the video to limit FPV to 1000.")
                iterator.close()
                continue

            def video_read_fn(x): return videoreader.read_frames(
                x, num_frames=fpv[vid])
            face_extractor = FaceExtractor(
                video_read_fn=video_read_fn, facedet=facedet)
            faces = face_extractor.process_video(video_glob[vid])
            try:
                faces_hc = torch.stack([transformer(image=frame['faces'][0])['image']
                                        for frame in faces if len(frame['faces'])])
            except:
                print(
                    f"Could not detect faces in the video with id {vid}. Hence, skipping it.")
                no_faces.append(vid)
                iterator.close()
                continue

            score, preds = ensemble_models(faces_hc[0:fpv[vid]])
            predictions_with_frame_level_data[video_glob[vid]] = [score, preds, faces, {'ensemble_score': sum(score.values())/(len(model_list))}, {
                'predicted_class': 'real' if sum(score.values())/(len(model_list)) < 0.3 else 'fake'}]
            predictions[video_glob[vid]] = [score, {'ensemble_score': sum(score.values())/(len(model_list))}, {
                'predicted_class': 'real' if sum(score.values())/(len(model_list)) < 0.3 else 'fake'}]

    videos_to_skip = no_faces + list(set(too_large)-set(no_faces))

    for _video_to_skip in videos_to_skip:
        video_idxs.remove(_video_to_skip)

    if(videos_to_skip):
        print(f"Skipped videos with id: {videos_to_skip}")

    if(len(videos_to_skip) > 0):
        print("ID of the videos that have been skipped:", videos_to_skip)
        if(len(too_large > 0)):
            print(
                "ID of the videos that have been skipped as they were too large in size:", too_large)
        if(len(no_faces > 0)):
            print(
                "ID of the videos that have been skipped as no faces were detected:", no_faces)
    else:
        print("No video has been skipped")

    print(f"IDs of the videos which were processed: {video_idxs}")

    if(not len(video_idxs)):
        print("No videos were processed. Exiting the program")
        return

    for ne in tqdm(video_idxs, desc='Annotating videos'):
        if(ne in videos_to_skip):
            continue

        if (ne < len(video_glob)):
            vid = cv2.VideoCapture(video_glob[ne])
        else:
            print("Error: index out of range")

        frame_count = 0
        face_count = 0
        writer = None
        success = True
        print(f"ne: {ne}, len(video_glob): {len(video_glob)}")
        vid = cv2.VideoCapture(video_glob[ne])
        real_frames = 0
        fake_frames = 0

        while success:
            success, img = vid.read()

            if writer is None:
                fourcc = cv2.VideoWriter_fourcc(*"MJPG")
                writer = cv2.VideoWriter(output_dir + os.path.basename(video_glob[ne]).split(
                    ".")[0]+'.avi', fourcc, 20, (img.shape[1], img.shape[0]), True)

            faces = predictions_with_frame_level_data[video_glob[ne]][2]
            if(face_count == fpv[ne]):
                break
            if face_count < fpv[ne] and faces[face_count]['frame_idx'] == frame_count:

                if len(faces[face_count]['detections']) > 0:
                    dect = faces[face_count]['detections'][0]

                ymin, xmin, ymax, xmax = dect[0], dect[1], dect[2], dect[3]
                num_models = len(model_list)

                p = {}  # contains frame level predictions for each model

                i = 0
                for j in predictions_with_frame_level_data[video_glob[ne]][1]:
                    try:
                        p[j] = predictions_with_frame_level_data[video_glob[ne]
                                                                 ][1][j][face_count-1]
                    except:
                        i = i + 1
                        print("skipping")
                        continue
                if(i > 0):
                    continue
                ensemble_pred_score = sum(p.values())/len(p)

                if ensemble_pred_score >= 0.3:
                    text = 'Fake:' + \
                        numberWithoutRounding(ensemble_pred_score, precision=4)
                    rgb = (0, 0, 255)
                    fake_frames = fake_frames+1

                else:
                    text = 'Real:' + \
                        numberWithoutRounding(ensemble_pred_score, precision=4)
                    rgb = (0, 255, 0)
                    real_frames = real_frames+1

                face_count += 1

            h, w, c = img.shape
            cv2.rectangle(img, (int(xmin), int(ymin)),
                          (int(xmax), int(ymax)), rgb, 2)
            text_y = ymin - 15 if ymin - 15 > 15 else ymin + 15
            cv2.putText(img, text, (int(xmin), int(text_y)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.75, rgb, 2)

            cv2.putText(img, 'Fake Frames ' + str(fake_frames), (int(w/2)+int(w/6),
                        int(h/2) + int(h/8)), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 0, 255), 2)
            cv2.putText(img, 'Real Frames ' + str(real_frames), (int(w/2) + int(w/6),
                        int(h/2) + int(h/15)), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 0), 2)

            lbls = ['Model']
            for n in p:
                lbls.append(n)

            offset = 0
            for vv, ll in enumerate(lbls):
                if(ll == 'TimmV2'):
                    lbls[vv] = 'V2'
                elif(ll == 'TimmV2ST'):
                    lbls[vv] = 'V2ST'
            for itr, word in enumerate(lbls):
                offset += int(h / len(lbls)) - 10
                cv2.putText(img, word, (20, offset),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 3)

            lbls_frame_pred = []
            for k in p:
                lbls_frame_pred.append(p[k])

            lbls_frame_pred_round = ['Score']
            for kk in lbls_frame_pred:
                lbls_frame_pred_round.append(numberWithoutRounding(kk, 4))

            offset = 0
            for f, g in enumerate(lbls_frame_pred_round):
                if(f != 0):
                    if('e' in g):
                        g = '0'
                if(f == 0):
                    offset += int(h / len(lbls_frame_pred_round)) - 10
                    cv2.putText(img, g, (130, offset),
                                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 3)
                    continue
                offset += int(h / len(lbls_frame_pred_round)) - 10
                if(float(g) >= 0.3):
                    # fake
                    cv2.putText(img, g, (130, offset),
                                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
                elif(float(g) < 0.3):
                    # real
                    cv2.putText(img, g, (130, offset),
                                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 3)

            writer.write(img)
            frame_count += 1

        writer.release()
    pclass = []
    for pr in predictions:
        pr_class = predictions[pr][2]['predicted_class']
        pclass.append(pr_class)
    data = {'video_path': [x for x in predictions.keys()],
            'prediction':  pclass}
    df = pd.DataFrame(data)

    if os.path.exists(output_dir+'predictions.csv'):
        df.to_csv(output_dir+'predictions.csv', mode='a', header=False)
    else:
        df.to_csv(output_dir+'predictions.csv')

    print("Annotated videos saved to "+output_dir)
    print("Predictions saved to " + output_dir + "predictions.csv")

    return predictions


def get_images_path(data_dir):

    ext = ['png', 'jpg', 'jpeg']    # Add image formats here
    files = []
    [files.extend(glob(data_dir + '*.' + e, recursive=True)) for e in ext]

    #image_names = ['{0:04}'.format(num) + ".png" for num in range(0, 2)]
    # all_image_paths = []
    # for i in range(0,2):
    #     all_image_paths.append(data_dir+image_names[i])
    # return all_image_paths, image_names ,files
    return files


def test_on_images(path_of_images, transformer, blazeface_dir, device, model, models_loaded, ensemble_models, json_path):
    facedet = BlazeFace().to(device)
    facedet.load_weights(blazeface_dir+"blazeface.pth")
    facedet.load_anchors(blazeface_dir+"anchors.npy")
    face_extractor = FaceExtractor(facedet=facedet)
    c = []
    for i in tqdm(path_of_images, desc='Predicting'):
        im = Image.open(i)
        im_face = face_extractor.process_image(img=im)
        im_face = im_face['faces'][0]
        faces_t = torch.stack([transformer(image=im)['image']
                              for im in [im_face]])

        with torch.no_grad():
            score, faces_pred = ensemble_models(faces_t.to(device))

        ensemble_score = sum(list(score.values())) / len(model)

        c.append(float(numberWithoutRounding(ensemble_score, 4)))

    for a, b in enumerate(c):
        if b <= 0.3:
            c[a] = 'real'
        else:
            c[a] = 'fake'

    result = dict(zip(path_of_images, c))

    with open(json_path, "w") as outfile:
        json.dump(result, outfile)

    print(f"Prediction results are saved in {json_path}")
    return result
