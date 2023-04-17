'''
mean
commentaires
cohérence des formalisme
segmentation
deux versions (draw_to_do)
suite
pylab
'''


from regression_model import load_model, NN_to_function
from attack_FGSM import attack_1
import scipy.stats
import pylab as pl
from random import random


def good_gaussian(sigma, mean=0):
    '''
    Ensures that the Gaussian is well-valued in Rd.
    '''
    def inner(x):
        d = len(x)
        return scipy.stats.multivariate_normal(mean*pl.ones(d), sigma*pl.identity(d)).rvs()
    return inner


def smoothing(f, n, G, p):
    """Returns the smoothed function of the function in input f

    Args:
        f (function): Rd -> R
        n (int): number of iterations for the random draw for the noise
        G (function): random variable for the noise. G takes x in entry, a list of length d. The function is defined to work with the random variable good_gaussian defined previously.
        p (float): depends on the method of draw chosen, here quantiles. p is between 0 and 1

    Returns:
        function: f_smoothed
    """

    qp = q_p(p, n)

    def smoothed_f(x):
        '''
        x is an element of Rd. Returns the value of smoothed_f(x), the smoothed version of f.
        '''
        h = {}
        sample = []
        for _ in range(n):
            x_with_noise = x+G(x)
            sample.append(float(f(x_with_noise)))
        sample.sort()
        h[tuple(x)] = sample[qp]

        return h[tuple(x)]

    return smoothed_f


def smoothing_exp(f, n, G):
    """

    Args:
        f (function)): from Rd to R
        n (int): number of iterations for the random draw of the noise
        G (function): random variable of the noise (e.g. standard normal distribution)

    Returns:
        function: smoothed version of f
    """

    def smoothed_f(x):
        '''
        x is an element of Rd
        '''
        g = {}
        sample = []
        for _ in range(n):
            x_with_noise = x+G(x)
            sample.append(float(f(x_with_noise)))
        sample.sort()
        g[tuple(x)] = exp(sample)

        return g[tuple(x)]

    return smoothed_f


def q_p(n, p):
    '''
    We do not take the average of two values. Here we choose to consider the lower index.
    '''
    return min(n-1, max(0, int((n+1)*p)-1))


def exp(sample):
    '''
    Returns the mean of the sample.
    '''
    res = 0
    for el in sample:
        res += el
    return res/len(sample)


def graph_diff(f, n, G, p):
    '''
    only works for d=1
    '''

    l_x = pl.linspace(2, 5, 1000)

    smoothed_f = smoothing(f, n, G, p)
    mean_f = smoothing_exp(f, n, G)

    l_f = [f([x]) for x in l_x]
    l_smoothed = [smoothed_f([x]) for x in l_x]
    l_mean = [mean_f([x]) for x in l_x]

    pl.plot(l_x, l_f, label='f')
    pl.plot(l_x, l_smoothed, label='f_p')
    pl.plot(l_x, l_mean, label='f_mean')

    pl.legend()

    pl.show()


graph_diff(lambda x: abs(pl.sin(x)), 10, good_gaussian(0.01), 0.5)


def phi(x, sigma, mean=0):
    '''
    Returns the cdf of the centered Gaussian.
    '''
    return scipy.stats.norm.cdf(x, mean, sigma)


def phi_minus_1(p, sigma, mean=0):
    '''
    Returns the inverse of the cdf of the centered Gaussian.
    '''
    return scipy.stats.norm.ppf(p, mean, sigma)


def smoothing_and_bounds_exp(f, n, sigma, l, u, alpha, epsilon):
    """
    To have the bounds of the paper, we need f to be normalized, and thus it should be bounded in [u, l].
    The formula only works with a centered Gaussian, so there is no need for G, only sigma.
    It is necessary to know the bound on the attacks epsilon (for now, I randomly put 0.1 for the 1D case).
    alpha is the confidence we want to have in the bound (0.999 for example).
    n is used to calculate f_smoothed and also for the quality of the bound because the larger n is, 
    the more confident we are.
    The security expression follows from the weak law of large numbers.

    Args:
        f (function): the function we want to certify
        n (int): number of iterations for the random draw of the noise
        sigma (float): standard deviation of the noise, has an impact on the quality of the bound, 
            the bigger the more trustworthy 
        l (float): lower bound for the value taken by f
        u (float): upper bound for the value taken by f
        epsilon (float): bound of the attack
        alpha (float): confidence rate of the bounds obtained for the output of the function

    Returns:
        function: f_smoothed
    """

    G = good_gaussian(sigma)

    security = (u-l)/(2*pl.sqrt(n*(1-alpha)))

    def f_smoothed(x):
        '''
        x is an element of Rd
        '''
        g = {}
        draws = []
        for _ in range(n):
            draws.append(G(x))

        sample = []
        for draw in draws:
            x_with_noise = x+draw
            sample.append(float(f(x_with_noise)))

            f_exp = exp(sample)
            g[tuple(x)] = l+(u-l)*phi((sigma*phi_minus_1((f_exp-l)/(u-l), sigma)-epsilon-security) /
                                      sigma, sigma), f_exp, l+(u-l)*phi((sigma*phi_minus_1((f_exp-l)/(u-l),
                                                                                           sigma)+epsilon+security)/sigma, sigma)

        return g[tuple(x)]

    return f_smoothed


def smoothing_and_bounds(f, n, sigma, p, alpha, epsilon):
    """Takes a function f and returns its smoothed function.

    Args:
        f (function): from Rd to R
        n (int): number of iterations of random noise generation
        sigma (float): standard deviation for her centered Gaussian distribution
        p (float): quantile, between 0 and 1
        alpha (float): confidence rate
        epsilon (float): bounds for the attack

    Returns:
        function: the smoothed version of the function f
    """

    G = good_gaussian(sigma)

    ql = q_lower(n, sigma, p, alpha, epsilon)
    qp = q_p(n, p)
    qu = q_upper(n, sigma, p, alpha, epsilon)

    '''
    All calculations will be done from the same sample.
    This makes it possible in particular to obtain the same result when recalculating f_smoothed at the same point.
    '''
    h = {}

    def f_smoothed(x):
        '''
        x is an element of Rd
        '''

        draws = []
        for _ in range(n):
            draws.append(G(x))

        sample = []
        for draw in draws:
            x_with_noise = x+draw
            sample.append(float(f(x_with_noise)))
        sample.sort()

        h[tuple(x)] = sample[ql], sample[qp], sample[qu]

        return h[tuple(x)]

    return f_smoothed


def q_lower(n, sigma, p, alpha, epsilon):
    p_l = phi(phi_minus_1(p, sigma)-epsilon/sigma, sigma)
    ql = max(0, int(n - 1 - scipy.stats.binom.ppf(alpha, n, 1 - p_l)))
    return ql


def q_upper(n, sigma, p, alpha, epsilon):
    p_u = phi(phi_minus_1(p, sigma)+epsilon/sigma, sigma)
    qu = min(n-1, int(scipy.stats.binom.ppf(alpha, n, p_u)))
    return qu


def graph_and_bounds(f, n, sigma, p, alpha, epsilon):
    smoothed_f = smoothing_and_bounds(f, n, sigma, p, alpha, epsilon)

    l_x = pl.linspace(2, 5, 1000)

    l_f = [f([x]) for x in l_x]
    l_smoothed = [smoothed_f([x])[1] for x in l_x]
    l_lower = [smoothed_f([x])[0] for x in l_x]
    l_upper = [smoothed_f([x])[2] for x in l_x]

    pl.plot(l_x, l_f, label='f')
    pl.plot(l_x, l_smoothed, label='smoothed_f')
    pl.plot(l_x, l_lower, label='f_l')
    pl.plot(l_x, l_upper, label='f_u')

    pl.legend()

    pl.show()


# graph_and_bounds(pl.sin, 10, 0.1, 0.5, 0.99, 0.1)


def graph_and_bounds_exp(f, n, sigma, l, u, alpha, epsilon):
    smoothed_f = smoothing_and_bounds_exp(f, n, sigma, l, u, alpha, epsilon)

    l_x = pl.linspace(-10, 10, 1000)

    l_f = [f([x]) for x in l_x]
    l_smoothed = [smoothed_f([x])[1] for x in l_x]
    l_lower = [smoothed_f([x])[0] for x in l_x]
    l_upper = [smoothed_f([x])[2] for x in l_x]

    pl.plot(l_x, l_f, label='f')
    pl.plot(l_x, l_smoothed, label='smoothed_f')
    pl.plot(l_x, l_lower, label='f_l')
    pl.plot(l_x, l_upper, label='f_u')

    pl.legend()

    pl.show()


# graph_and_bounds_mean(pl.sin, 1000, 1, -1, 1, 0.99, 0.1)

# test = NN_to_function(load_model())
# test_smoothed = smoothing_and_bounds(test, 100, 1, 0.5, 0.9, 1)
# print(test_smoothed([17.76, 42.42, 1009.09, 66.26]),
#       test([17.76, 42.42, 1009.09, 66.26]))


def p_minus(n, p, alpha, precision):
    """_summary_

    Args:
        n (int): number of iterations of random noise generation
        p (float): quantile, between 0 and 1
        alpha (float): confidence rate of the output
        precision (float): bound for the dichotomy method

    Returns:
        _type_: _description_
    """
    a = 0
    b = 1
    while b-a > precision:
        m = (a+b)/2
        if scipy.stats.binom.cdf(q_p(n, p), n, m) > alpha:
            a = m
        else:
            b = m
    return a


def p_plus(n, p, alpha, precision):
    """_summary_

    Args:
        n (int): number of iterations of random noise generation
        p (float): quantile, between 0 and 1
        alpha (float): confidence rate of the output
        precision (float): bound for the dichotomy method

    Returns:
        _type_: _description_
    """
    a = 0
    b = 1
    while b-a > precision:
        m = (a+b)/2
        if scipy.stats.binom.cdf(n-1-q_p(n, p), n, 1-m) > alpha:
            b = m
        else:
            a = m
    return b


def max_bound(f, n, sigma, p, alpha, epsilon, precision):
    """Takes a function f and returns its smoothed function.

    Args:
        f (function): from Rd to R
        n (int): number of iterations of random noise generation
        sigma (float): standard deviation for her centered Gaussian distribution
        p (float): quantile, between 0 and 1
        alpha (float): confidence rate
        epsilon (float): bounds for the attack
        precision (float) : how precise p_minus and p_plus should be

    Returns:
        function: the smoothed version of the function f
    """

    G = good_gaussian(sigma)

    ql = q_lower(n, sigma, p, alpha, epsilon)
    qp = q_p(n, p)
    qu = q_upper(n, sigma, p, alpha, epsilon)
    qlmax = q_lower(n, sigma, p_minus(n, p, alpha, precision), alpha, epsilon)
    qumax = q_upper(n, sigma, p_plus(n, p, alpha, precision), alpha, epsilon)

    '''
    All calculations will be done from the same sample.
    This makes it possible in particular to obtain the same result when recalculating f_smoothed at the same point.
    '''

    def f_smoothed(x):
        '''
        x is an element of Rd
        '''
        h = {}
        draws = []
        for _ in range(n):
            draws.append(G(x))

        sample = []
        for draw in draws:
            x_with_noise = x+draw
            sample.append(float(f(x_with_noise)))
        sample.sort()

        h[tuple(x)] = sample[qlmax], sample[ql], sample[qp], sample[qu], sample[qumax]

        return h[tuple(x)]

    return f_smoothed


def max_bound_exp(f, n, sigma, l, u, alpha, epsilon):
    """
    To have the bounds of the paper, we need to normalize f, and thus it should be bounded in [u, l].
    The formula only works with a centered Gaussian, so there is no need for G, only sigma.
    It is necessary to know the bound on the attacks epsilon (for now, I randomly put 0.1 for the 1D case).
    alpha is the confidence we want to have in the bound (0.999 for example).
    n is used to calculate f_smoothed and also for the quality of the bound because the larger n is, 
    the more confident we are.
    The security expression follows from the weak law of large numbers.

    Args:
        f (function): _description_
        n (int): number of iterations for the random draw of the noise
        sigma (float): standard deviation of the noise, has an impact on the quality of the bound, 
            the bigger the more trustworthy 
        l (float): lower bound for the value taken by f
        u (float): upper bound for the value taken by f
        alpha (float): confidence rate of the bounds obtained for the output of the function
        epsilon (float): bound of the attack

    Returns:
        function: f_smoothed
    """

    G = good_gaussian(sigma)
    security = (u-l)/(2*pl.sqrt(n*(1-alpha)))

    def f_smoothed(x):
        '''
        x is an element of Rd
        '''
        g = {}
        draws = []
        for _ in range(n):
            draws.append(G(x))

        sample = []
        for draw in draws:
            x_with_noise = x+draw
            sample.append(float(f(x_with_noise)))

            f_mean = exp(sample)
            f_l = l+(u-l)*phi((sigma*phi_minus_1((f_mean-l) /
                                                 (u-l), sigma)-epsilon-security)/sigma, sigma)
            f_u = l+(u-l)*phi((sigma*phi_minus_1((f_mean-l) /
                                                 (u-l), sigma)+epsilon+security)/sigma, sigma)
            g[tuple(x)] = f_l-security, f_l, f_mean, f_u, f_u+security

        return g[tuple(x)]

    return f_smoothed


def max_graph(f, n, sigma, p, alpha, epsilon, precision):
    smoothed_f = max_bound(f, n, sigma, p, alpha, epsilon, precision)

    l_x = pl.linspace(2, 5, 2)

    l_f = [f([x]) for x in l_x]
    l_smoothed = [smoothed_f([x])[2] for x in l_x]
    l_lower = [smoothed_f([x])[1] for x in l_x]
    l_upper = [smoothed_f([x])[3] for x in l_x]
    l_lmax = [smoothed_f([x])[0] for x in l_x]
    l_umax = [smoothed_f([x])[4] for x in l_x]

    pl.plot(l_x, l_f, label='f')
    pl.plot(l_x, l_smoothed, label='smoothed_f')
    pl.plot(l_x, l_lower, label='f_l')
    pl.plot(l_x, l_upper, label='f_u')
    pl.plot(l_x, l_lmax, label='f_lmax')
    pl.plot(l_x, l_umax, label='f_umax')

    pl.legend()

    pl.show()


# max_graph(lambda x: abs(pl.sin(x)), 1000, 1, 0.5, 0.99, 0.1, 0.001)


def norme_2(x):
    res = 0
    for el in x:
        res += el**2
    return pl.sqrt(res)


def attack_set(x, epsilon, n_attack):
    l_attack = []
    d = len(x)
    for i in range(n_attack):
        attack = [random()-0.5 for _ in range(d)]
        attack = pl.array(attack)*epsilon/norme_2(attack)
        l_attack.append(attack)
    return l_attack


def out_of_bound(f, n, sigma, x, p, alpha, epsilon, precision, n_attack):
    """
    simulates attacks to see if the proportion of tries out of bound is close to the expected value.
    """
    res = [0]*5
    l_attack = attack_set(x, epsilon, n_attack)
    l_x = [x+attack for attack in l_attack]
    smoothed_f = max_bound(f, n, sigma, p, alpha, epsilon, precision)
    lower = smoothed_f(x)[1]
    upper = smoothed_f(x)[3]
    lmax = smoothed_f(x)[0]
    umax = smoothed_f(x)[4]
    for x_with_noise in l_x:
        answer = smoothed_f(x_with_noise)[2]
        if answer < lmax:
            res[0] += 1
        elif lmax <= answer < lower:
            res[1] += 1
        elif lower <= answer < upper:
            res[2] += 1
        elif upper <= answer < umax:
            res[3] += 1
        elif umax <= answer:
            res[4] += 1
    return pl.array(res)/len(l_attack)

# print(out_of_bound(NN_to_function(load_model()),
#       100, 1, [17.76, 42.42, 1009.09, 66.26], 0.5, 0.5, 1, 0.001, 100))


def out_of_bound_same_attack(f, n, sigma, x, p, alpha, epsilon, precision, n_attack, attack):
    """
    simulates attacks to see if the proportion of tries out of bound is close to the expected value.
    """
    res = [0]*5
    l_attack = attack_set(x, epsilon, n_attack)
    l_x = [x+attack for attack in l_attack]
    smoothed_f = max_bound(f, n, sigma, p, alpha, epsilon, precision)
    lower = smoothed_f(x)[1]
    upper = smoothed_f(x)[3]
    lmax = smoothed_f(x)[0]
    umax = smoothed_f(x)[4]
    for x_with_noise in l_x:
        answer = smoothed_f(x_with_noise)[2]
        if answer < lmax:
            res[0] += 1
        elif lmax <= answer < lower:
            res[1] += 1
        elif lower <= answer < upper:
            res[2] += 1
        elif upper <= answer < umax:
            res[3] += 1
        elif umax <= answer:
            res[4] += 1
    return pl.array(res)/len(l_attack)

# print(out_of_bound(NN_to_function(load_model()),
#       100, 1, [17.76, 42.42, 1009.09, 66.26], 0.5, 0.5, 1, 0.001, 100))


def out_of_bound_same_attack(f, n, sigma, x, p, alpha, epsilon, precision, n_attack, attack):
    """
    simulates attacks to see if the proportion of tries out of bound is close to the meanected value.
    """
    res = [0]*5
    smoothed_f = max_bound(f, n, sigma, p, alpha, epsilon, precision)
    lower = smoothed_f(x)[1]
    upper = smoothed_f(x)[3]
    lmax = smoothed_f(x)[0]
    umax = smoothed_f(x)[4]
    x_with_noise = x+pl.array(attack[0])
    for _ in range(n_attack):
        answer = smoothed_f(x_with_noise)[2]
        if answer < lmax:
            res[0] += 1
        elif lmax <= answer < lower:
            res[1] += 1
        elif lower <= answer < upper:
            res[2] += 1
        elif upper <= answer < umax:
            res[3] += 1
        elif umax <= answer:
            res[4] += 1
    return pl.array(res)/n_attack


print(out_of_bound_same_attack(NN_to_function(load_model()),
      100, 1, [17.76, 42.42, 1009.09, 66.26], 0.5, 0.99, 1, 0.001, 1, attack_1(load_model(), [[[17.76, 42.42, 1009.09, 66.26], [468.27]]], 1)))


def Rd_to_R(f, d):
    def inner(x):
        return f(list(x)*d)
    return inner


# max_graph(Rd_to_R(NN_to_function(load_model()), 4),
#           3, 1, 0.5, 0.99, 0.1, 0.001)
