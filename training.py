# -*- coding: UTF-8 -*-
# 単純な関数のデータを与えて元のデータを予測させてみる
# 学習用データが(TesraK80の)メモリに乗らないため,Generatorを使ってバッチごとにデータをロードさせる感じで
# 20万件のデータを200件ずつ取り出す
from keras.models import Sequential
from keras.layers.core import Dense, Dropout, Activation
from keras.layers import LeakyReLU, PReLU
from keras.callbacks import EarlyStopping, TensorBoard
import keras.backend.tensorflow_backend as KTF
import tensorflow as tf
import numpy as np
import matplotlib.pyplot as plt
import os
from read_training_data import read_csv_type3

def batch_iter(data, labels, batch_size, shuffle=True):
    num_batches_per_epoch = int((len(data) - 1) / batch_size) + 1

    def data_generator():
        data_size = len(data)
        while True:
            # Shuffle the data at each epoch
            if shuffle:
                shuffle_indices = np.random.permutation(np.arange(data_size))
                shuffled_data = data[shuffle_indices]
                shuffled_labels = labels[shuffle_indices]
            else:
                shuffled_data = data
                shuffled_labels = labels

            for batch_num in range(num_batches_per_epoch):
                start_index = batch_num * batch_size
                end_index = min((batch_num + 1) * batch_size, data_size)
                X = shuffled_data[start_index: end_index]
                y = shuffled_labels[start_index: end_index]
                yield X, y

    return num_batches_per_epoch, data_generator()

def save_my_log(source, case_number, fname_lift_train, fname_shape_train, model_sum):
    with open(source + str(case_number).zfill(4) + "_log.txt", "w") as f:
        f.write("case number :" + str(case_number).zfill((3)) + "\n")
        f.write("training_data of Lift :" + fname_lift_train + "\n")
        f.write("training_data of Shape :" + fname_shape_train + "\n")
        f.write("model summary" + "\n")
        f.write(str(model_sum) + "\n")

def get_case_number(source, env, case_number):
    flag = 0
    source = source + "learned\\"
    if env == "Colab":
        source = source.replace("\\", "/")
        case_number += 10000
    while flag == 0:
        if os.path.exists(source + str(case_number).zfill(5) + "_mlp_model_.json"):
            case_number += 1
        else:
            flag = 1
    return str(case_number).zfill(5)

def main(fname_lift_train, fname_shape_train, fname_lift_test, fname_shape_test, case_number, case_type=3, env="Lab"):
    r_rate = [1, 2, 4, 8]
    for rr in r_rate:
        if rr == 1:
            s_odd = 0   # 全部読みだす
        elif fname_shape_train.find("fourier") != -1:
            s_odd = 3   # 前方から読み出す(fourier用)
        else:
            s_odd = 4   # 全体にわたって等間隔に読み出す(equidistant, dense用)

        old_session = KTF.get_session()

        with tf.Graph().as_default():
            source = "Incompressible_Invicid\\training_data\\"
            if env == "Lab":
                source = "D:\\Toyota\\Data\\" + source
                case_num = get_case_number(source, env, case_number)
                log_name = "learned\\" + case_num + "_tb_log.hdf5"
                json_name = "learned\\" + case_num + "_mlp_model_.json"
                weight_name = "learned\\" + case_num + "_mlp_weight.h5"
            elif env == "Colab":
                source = "/content/drive/Colab Notebooks/" + source.replace("\\", "/")
                case_num = get_case_number(source, env, case_number)
                log_name = "learned/" + case_num + "_log.hdf5"
                json_name = "learned/" + case_num + "_mlp_model_.json"
                weight_name = "learned/" + case_num + "_mlp_weight.h5"

            session = tf.Session('')
            KTF.set_session(session)
            KTF.set_learning_phase(1)

            model = Sequential()
            if case_type == 3:
                X_train, y_train = read_csv_type3(source, fname_lift_train, fname_shape_train, shape_odd = s_odd, read_rate = rr)
                x_test, y_test = read_csv_type3(source, fname_lift_test, fname_shape_test, shape_odd=s_odd, read_rate=rr)

            input_vector_dim = X_train.shape[1]
            with tf.name_scope("inference") as scope:
                model.add(Dense(units=2, input_dim=input_vector_dim))
                model.add(LeakyReLU())
                model.add(Dense(units=16))
                model.add(LeakyReLU())
                """
                model.add(Dense(units=128))
                model.add(LeakyReLU())
                model.add(Dense(units=192))
                model.add(LeakyReLU())
                model.add(Dense(units=2048))
                model.add(LeakyReLU())
                model.add(Dense(units=2048))
                model.add(LeakyReLU())
                """
                """
                model.add(Dense(units=512))
                model.add(LeakyReLU())
    
                for i in range(5):
                    model.add(Dense(units = 512))
                    model.add(LeakyReLU())
                    # model.add(Dropout(0.5))
                # model.add(Dense(units=half, activation='relu'))
                # model.add(Dropout(0.5))
                """
                model.add(Dense(units=1))

            model.summary()

            save_my_log(source, case_number, fname_lift_train, fname_shape_train, model.summary())
            # es_cb = EarlyStopping(monitor='val_loss', patience=0, verbose=0, mode='auto')
            tb_cb = TensorBoard(log_dir=source + log_name, histogram_freq=0, write_grads=True)

            model.compile(loss="mean_squared_error",
                          optimizer='Adam')

            batch_size = 500
            train_steps, train_batches = batch_iter(X_train, y_train, batch_size)
            valid_steps, valid_batches = batch_iter(x_test, y_test, batch_size)
            """
            model.fit(x=X_train, y=y_train,
                      batch_size=600, nb_epoch=1000,
                      validation_split=0.05, callbacks=[tb_cb])
            """
            model.fit_generator(train_batches, train_steps,
                                epochs=1000,
                                validation_data=valid_batches,
                                validation_steps=valid_steps,
                                callbacks=[tb_cb])
            # X_train: [number, angle, shape001, shape002, ..., shapeMAX]
            # y_train: [number, lift]
            # 適当に中央付近の翼を抜き出しての-40-38degreeをプロットさせてみる
            tekito = 1306 * 40  # NACA2613 or NACA2615
            plt.figure()
            plt.plot(X_train[tekito:tekito+40, 0], y_train[tekito:tekito+40])
            plt.plot(X_train[tekito:tekito+40, 0], model.predict(X_train)[tekito:tekito+40])
            plt.savefig(source + case_num + "_train.png")

            y_predict = model.predict(x_test)
            tekito = (99 + 13) * 40 # 22012
            plt.figure()
            plt.plot(x_test[tekito:tekito+40, 0], y_test[tekito:tekito+40])
            plt.plot(x_test[tekito:tekito+40, 0], y_predict[tekito:tekito+40])
            plt.savefig(source + case_num + "_test.png")

        json_string = model.to_json()
        open(source + json_name, 'w').write(json_string)
        model.save_weights(source + weight_name)
        KTF.set_session(old_session)


if __name__ == '__main__':
    # env_in = input("Please set envirionment: 0:Lab, 1:Colab")
    env_in = str(1)
    if env_in == str(0):
        env = "Lab"
    elif env_in == str(1):
        env = "Colab"
    else:
        print("env_error")
        exit()

    # shape_type = input("please set shape_type: 0:fourier, 1:equidistant, 2:dense")
    shape_type = str(0)
    fname_lift_train = "NACA4\\s0000_e5000_a040_odd.csv"
    fname_lift_test = "NACA5\\s21001_e25199_a040.csv"

    if shape_type == str(0):
        fname_shape_train = "NACA4\\shape_fourier_5000_odd.csv"
        fname_shape_test = "NACA5\\shape_fourier_all.csv"
        case_number = 0

    elif shape_type == str(1):
        fname_shape_train = "NACA4\\shape_equidistant_5000_odd.csv"
        fname_shape_test = "NACA5\\shape_equidistant_all.csv"
        case_number = 1000

    elif shape_type == str(2):
        fname_shape_train = "NACA4\\shape_crowd_0.1_0.15_30_50_20_5000_odd.csv"
        fname_shape_test = "NACA5\\shape_crowd_0.1_0.15_30_50_20_all.csv"
        case_number = 2000
    else:
        print("shape_type error")
        exit()

    if env == "Colab":
        fname_lift_train = fname_lift_train.replace("\\", "/")
        fname_shape_train = fname_shape_train.replace("\\", "/")
        fname_lift_test = fname_lift_test.replace("\\", "/")
        fname_shape_test = fname_shape_test.replace("\\", "/")

    main(fname_lift_train, fname_shape_train, fname_lift_test, fname_shape_test, case_number, case_type=3, env=env)