from functools import wraps

import numpy as np
from scipy.stats import norm, t


def quantile(dist):
    """
    Used with PDF or CDF

    Converts the random vectors to their quantile before passing into the PDF or CDF function. Random vectors need to
    be converted to their quantile for PDF or CDF to work correctly. Also ensures that nan values are converted to
    nan. The PDF/CDF functions returns 0 if the vector has an nan in it.

    :param dist: str
        type of distribution, either Gaussian (normal), or Student (t)
    :return: Callable
        Wrapped PDF or CDF function
    """

    if dist.casefold() in {'norm', 'gaussian', 'normal'}:

        def decorator(func):
            @wraps(func)
            def with_quantile(self, x: np.ndarray, log=False):
                q = norm.ppf(x)
                if q.ndim == 1:
                    q = q.reshape(1, -1)

                values = func(self, q, log)

                # CDF sometimes returns floats, need to make it a 1D array
                if not hasattr(values, '__len__'):
                    values = np.array([values])

                # check values for nan
                values[np.isnan(q).any(1)] = np.nan

                # only 1 value, extract float
                return values[0] if len(values) == 1 else values

            return with_quantile

        return decorator

    elif dist.casefold() in {'t', 'student'}:

        def decorator(func):
            @wraps(func)
            def with_quantile(self, x: np.ndarray, log=False):
                q = t.ppf(x, self.params.df)
                if q.ndim == 1:
                    q = q.reshape(1, -1)

                values = func(self, q, log)

                # CDF sometimes returns floats, need to make it a 1D array
                if not hasattr(values, '__len__'):
                    values = np.array([values])

                # check values for nan
                values[np.isnan(q).any(1)] = np.nan

                # only 1 value, extract float
                return values[0] if len(values) == 1 else values

            return with_quantile

        return decorator
    else:
        raise ValueError(f"Distribution specified '{dist}' is not supported")