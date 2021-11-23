from models.utils import *
import tensorflow as tf


def res_block_initial(x, num_filters, kernel_size, strides, name):
    """Residual Unet block layer for first layer
    In the residual unet the first residual block does not contain an
    initial batch normalization and activation so we create this separate
    block for it.
    Args:
        x: tensor, image or image activation
        num_filters: list, contains the number of filters for each subblock
        kernel_size: int, size of the convolutional kernel
        strides: list, contains the stride for each subblock convolution
        name: name of the layer
    Returns:
        x1: tensor, output from residual connection of x and x1
    """
    if len(num_filters) == 1:
        num_filters = [num_filters[0], num_filters[0]]

    x1 = Conv2D(num_filters[0], kernel_size, strides=strides[0], padding='same', name=name + '_1')(x)
    x1 = BatchNormalization()(x1)
    x1 = Activation('relu')(x1)
    x1 = Conv2D(num_filters[1], kernel_size, strides=strides[1], padding='same', name=name + '_2')(x1)

    x = Conv2D(num_filters[-1], 1, strides=1, padding='same', name=name + '_shortcut')(x)
    x = BatchNormalization()(x)

    x1 = Add()([x, x1])

    return x1


def res_block(x, num_filters, kernel_size, strides, name):
    """Residual Unet block layer
    Consists of batch norm and relu, folowed by conv, batch norm and relu and
    final convolution. The input is then put through
    Args:
        x: tensor, image or image activation
        num_filters: list, contains the number of filters for each subblock
        kernel_size: int, size of the convolutional kernel
        strides: list, contains the stride for each subblock convolution
        name: name of the layer
    Returns:
        x1: tensor, output from residual connection of x and x1
    """
    if len(num_filters) == 1:
        num_filters = [num_filters[0], num_filters[0]]

    x1 = BatchNormalization()(x)
    x1 = Activation('relu')(x1)
    x1 = Conv2D(num_filters[0], kernel_size, strides=strides[0], padding='same', name=name + '_1')(x1)

    x1 = BatchNormalization()(x1)
    x1 = Activation('relu')(x1)
    x1 = Conv2D(num_filters[1], kernel_size, strides=strides[1], padding='same', name=name + '_2')(x1)

    x = Conv2D(num_filters[-1], 1, strides=strides[0], padding='same', name=name + '_shortcut')(x)
    x = BatchNormalization()(x)

    x1 = Add()([x, x1])

    return x1


def upsample(x, target_size):
    """"Upsampling function, upsamples the feature map
    Deep Residual Unet paper does not describe the upsampling function
    in detail. Original Unet uses a transpose convolution that downsamples
    the number of feature maps. In order to restrict the number of
    parameters here we use a bilinear resampling layer. This results in
    the concatentation layer concatenting feature maps with n and n/2
    features as opposed to n/2  and n/2 in the original unet.
    Args:
        x: tensor, feature map
        target_size: size to resize feature map to
    Returns:
        x_resized: tensor, upsampled feature map
    """
    x_resized = Lambda(lambda x: tf.image.resize(x, target_size))(x)

    return x_resized


def encoder(x, num_filters, kernel_size):
    """Unet encoder
    Args:
        x: tensor, output from previous layer
        num_filters: list, number of filters for each decoder layer
        kernel_size: int, size of the convolutional kernel
    Returns:
        encoder_output: list, output from all encoder layers
    """
    x = res_block_initial(x, [num_filters[0]], kernel_size, strides=[1, 1], name='layer1')

    encoder_output = [x]
    for i in range(1, len(num_filters)):
        layer = 'encoder_layer' + str(i)
        x = res_block(x, [num_filters[i]], kernel_size, strides=[2, 1], name=layer)
        encoder_output.append(x)

    return encoder_output


def decoder(x, encoder_output, num_filters, kernel_size):
    """Unet decoder
    Args:
        x: tensor, output from previous layer
        encoder_output: list, output from all previous encoder layers
        num_filters: list, number of filters for each decoder layer
        kernel_size: int, size of the convolutional kernel
    Returns:
        x: tensor, output from last layer of decoder
    """
    for i in range(1, len(num_filters) + 1):
        layer = 'decoder_layer' + str(i)
        target_size = encoder_output[-i].shape[1:3]
        x = upsample(x, target_size)
        # print(x.shape, encoder_output[-i].shape)
        x = Concatenate(axis=-1)([x, encoder_output[-i]])
        x = res_block(x, [num_filters[-i]], kernel_size, strides=[1, 1], name=layer)

    return x


def res_unet(shape=(256, 256, 3), kernel_size=(3, 3), num_classes=1):
    """
    Road Extraction by Deep Residual U-Net.
    Paper: https://arxiv.org/pdf/1711.10684.pdf
    Code from: https://github.com/dmolony3/ResUNet

    Function that generates a residual unet
    Args:
        shape: shape of input images.
        kernel_size: size of the kernel, applied to all convolutions.
        num_classes: int, number of output classes for the output.
    Returns:
        model: tensorflow keras model for residual unet architecture.
    """
    n_filters = [64, 128, 256]

    x = Input(shape)

    encoder_output = encoder(x, n_filters, kernel_size)

    # bridge layer, number of filters is double that of the last encoder layer
    bridge = res_block(encoder_output[-1], [n_filters[-1] * 2], kernel_size, strides=[2, 1], name='bridge')

    # print(encoder_output[-1].shape)
    decoder_output = decoder(bridge, encoder_output, n_filters, kernel_size)

    outputs = Conv2D(num_classes, (1, 1), padding='same', name='output')(decoder_output)
    outputs = Activation("sigmoid")(outputs)

    model = Model(x, outputs, name="res_unet")

    return model


if __name__ == "__main__":
    model = res_unet()
    model.summary()
