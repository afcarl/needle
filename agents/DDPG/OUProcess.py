import numpy as np

def OUProcess(theta=0.15, sigma=0.2, dt=1., shape=1):
    x = 0.
    while True:
        for i in range(1):
            x += -theta * x * dt + sigma * np.sqrt(dt) * np.random.randn(shape)
        yield x
