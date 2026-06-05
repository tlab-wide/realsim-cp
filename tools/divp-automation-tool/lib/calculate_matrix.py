import numpy as np


def calculate_rotation_matrix(roll, pitch, yaw):
    rotate_x = np.array(
        [[1, 0, 0], [0, np.cos(roll), -np.sin(roll)], [0, np.sin(roll), np.cos(roll)]]
    )
    rotate_y = np.array(
        [
            [np.cos(pitch), 0, np.sin(pitch)],
            [0, 1, 0],
            [-np.sin(pitch), 0, np.cos(pitch)],
        ]
    )
    rotate_z = np.array(
        [[np.cos(yaw), -np.sin(yaw), 0], [np.sin(yaw), np.cos(yaw), 0], [0, 0, 1]]
    )

    return rotate_z @ rotate_y @ rotate_x


def calculate_transform_matrix(angle, translation):
    rotation = calculate_rotation_matrix(-angle[0], -angle[1], -angle[2])
    transform_matrix = np.eye(4)
    transform_matrix[0:3, 0:3] = rotation
    transform_matrix[0:3, 3] = translation
    return transform_matrix


def convert_euler_to_quaternion(roll, pitch, yaw):
    cos_roll = np.cos(roll * 0.5)
    sin_roll = np.sin(roll * 0.5)
    cos_pitch = np.cos(pitch * 0.5)
    sin_pitch = np.sin(pitch * 0.5)
    cos_yaw = np.cos(yaw * 0.5)
    sin_yaw = np.sin(yaw * 0.5)

    qx = sin_roll * cos_pitch * cos_yaw - cos_roll * sin_pitch * sin_yaw
    qy = cos_roll * sin_pitch * cos_yaw + sin_roll * cos_pitch * sin_yaw
    qz = cos_roll * cos_pitch * sin_yaw - sin_roll * sin_pitch * cos_yaw
    qw = cos_roll * cos_pitch * cos_yaw + sin_roll * sin_pitch * sin_yaw

    return [qx, qy, qz, qw]
