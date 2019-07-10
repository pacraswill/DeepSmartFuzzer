import numpy as np
import itertools
import image_transforms

def DeepHunter(I, coverage, K=64):
    F = np.array([]).reshape(0, 28, 28, 1)
    T = Preprocess(I)
    B, B_id = SelectNext(T)

    while B is not None:
        S = Sample(B)
        Ps = PowerSchedule(S, K)
        B_new = np.array([]).reshape(0, 28, 28, 1)
        for s_i in range(len(S)):
            I = S[s_i]
            for i in range(1, Ps(s_i)+1):
                I_new = Mutate(I)
                if isFailedTest(I_new):
                    F += np.concatenate((F, [I_new]))
                elif isChanged(I, I_new):
                    B_new = np.concatenate((B_new, [I_new]))

        if len(B_new) > 0:
            cov = Predict(coverage, B_new)
            print("coverage:", coverage.get_current_coverage())
            if CoverageGain(cov):
                B_c, Bs = T
                B_c += [1]
                Bs +=  [B_new]
                BatchPrioritize(T, B_id)
        
        B, B_id = SelectNext(T)

def Preprocess(I, batch_size=64):
    _I = np.random.permutation(I)
    Bs = np.array_split(_I, range(64,len(_I),64))
    return list(np.ones(len(Bs))), Bs

def calc_priority(B_ci, p_min=0.01, gama=0.9):
    if B_ci < (1-p_min) * gama:
        return 1 - B_ci / gama
    else:
        return p_min

def SelectNext(T):
    B_c, Bs = T
    B_p = [calc_priority(B_c[i]) for i in range(len(B_c))]
    c = np.random.choice(len(Bs), p=B_p/np.sum(B_p))
    return Bs[c], c

def Sample(B, batch_size=16):
    c = np.random.choice(len(B), size=batch_size, replace=False)
    return B[c]

class INFO:
    def __init__(self):
        self.dict = {}
    
    def __getitem__(self, i):
        _i =str(i)
        if _i in self.dict:
            return self.dict[_i]
        else:
            I0, I0_new, state = np.copy(i), np.copy(i), 0
            return I0, I0_new, state

    def __setitem__(self, i, s):
        _i = str(i)
        self.dict[_i] = s
        return self.dict[_i]

info = INFO() 

def PowerSchedule(S, K, beta=0.1):
    global info
    potentials = []
    for i in range(len(S)):
        I = S[i]
        I0, I0_new, state = info[I]
        p = beta * 255 * I.size - np.sum(np.abs(I - I0_new))
        potentials.append(p)
    potentials = np.array(potentials) / np.sum(potentials)

    def Ps(I_id):
        p = potentials[I_id]
        return int(np.ceil(p*K))
    
    return Ps


def isFailedTest(I_new):
    return False

def isChanged(I, I_new):
    return np.any(I != I_new)

def Predict(coverage, B_new):
    print("Predict B_new.shape", np.array(B_new).shape)
    _, cov = coverage.step(B_new, update_state=False)
    return cov

def CoverageGain(cov):
    return cov > 0

def BatchPrioritize(T, B_id):
    B_c, Bs = T
    B_c[B_id] -= 0.1


translation = list(itertools.product([getattr(image_transforms,"image_translation")], [(10+10*k,10+10*k) for k in range(10)]))
scale = list(itertools.product([getattr(image_transforms, "image_scale")], [(1.5+0.5*k,1.5+0.5*k) for k in range(10)]))
shear = list(itertools.product([getattr(image_transforms, "image_shear")], [(-1.0+0.1*k,0) for k in range(10)]))
rotation = list(itertools.product([getattr(image_transforms, "image_rotation")], [3+3*k for k in range(10)]))
contrast = list(itertools.product([getattr(image_transforms, "image_contrast")], [1.2+0.2*k for k in range(10)]))
brightness = list(itertools.product([getattr(image_transforms, "image_brightness")], [10+10*k for k in range(10)]))
blur = list(itertools.product([getattr(image_transforms, "image_blur")], [k+1 for k in range(10)]))

G = translation + rotation
P = contrast + brightness #+ blur

def Mutate(I, TRY_NUM=100):
    global info
    #print("I.shape", I.shape)
    I0, I0_new, state = info[I]
    for i in range(1, TRY_NUM):
        if state == 0:
            t, p = randomPick(G + P)
        else:
            t, p = randomPick(P)

        I_new = t(np.copy(I), p).reshape(28,28,1)
        I_new = np.clip(I_new, 0, 255)
        if f(I0_new, I_new):
            if (t, p) in G:
                state = 1
                I0_new = t(np.copy(I0), p)
            info[I_new] = (np.copy(I0), np.copy(I0_new), state)
            return I_new

    return I

def randomPick(A):
    c = np.random.randint(0, len(A))
    return A[c]

def f(I, I_new, beta=0.1, alpha=0.1):
    if(np.sum(np.abs(I-I_new)) < alpha * I.size):
        return False
        return np.all(I-I_new <= 255)
    else:
        return True
        return np.all(I-I_new <= beta*255)