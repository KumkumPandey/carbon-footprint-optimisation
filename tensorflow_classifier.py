import tensorflow as tf
from tensorflow import keras
from keras import layers
import numpy as np

# 1. Dummy Data (Replace with real image data)
def create_dummy_dataset(num_images=100):
    images = np.random.rand(num_images, 64, 64, 3) * 255
    labels = np.random.randint(0, 2, num_images) # 0: Clear, 1: Congested
    return images, labels

X_train, y_train = create_dummy_dataset()
X_test, y_test = create_dummy_dataset(20)

# 2. Define CNN Model
model = keras.Sequential([
    layers.Rescaling(1./255, input_shape=(64, 64, 3)),
    layers.Conv2D(32, 3, activation='relu'),
    layers.MaxPooling2D(),
    layers.Conv2D(64, 3, activation='relu'),
    layers.MaxPooling2D(),
    layers.Flatten(),
    layers.Dense(128, activation='relu'),
    layers.Dense(1, activation='sigmoid')
])

# 3. Compile and Train
model.compile(optimizer='adam',
              loss='binary_crossentropy',
              metrics=['accuracy'])

model.fit(X_train, y_train, epochs=5, validation_data=(X_test, y_test))

# 4. Save the model
model.save('road_condition_classifier.h5')
print("TensorFlow model saved successfully as 'road_condition_classifier.h5'!")