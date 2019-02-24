import pickle
from os.path import join as pjoin, dirname, exists
from typing import Optional, Iterable, Callable

import numpy as np
from scipy.interpolate import UnivariateSpline

from copulae.copula import BaseCopula
from copulae.stats import corr

__all__ = ['_DataMixin']


class _DataMixin:
    def __init__(self, copula: BaseCopula, ss: float, seed: Optional[int] = None):
        self.copula = copula
        self.file_path = pjoin(dirname(__file__), 'data_funcs.p')
        self.nsim = 50000  # estimated number of trials for correlations to somewhat converge
        self.ss = ss  # tuning parameter

        if seed is not None:
            np.random.seed(seed)

        self._meta_data = self._load_func_dict()

    @property
    def file_exists(self):
        return exists(self.file_path)

    def _load_func_dict(self) -> dict:
        """
        Loads the meta data in the pickle file

        :return: dict
            dictionary containing the meta data
        """
        if not self.file_exists:
            return {}
        with open(self.file_path, 'rb') as f:
            return pickle.load(f)

    def load_copula_data(self, func_name: str):
        """
        Returns the function stored in the meta data file.

        :param func_name: str
            function name
        :return: Callable
        """
        return self._meta_data[func_name]

    def save_copula_data(self, func_name: str, func: Callable):
        """
        Saves the meta data (callable object) into the data pickle file

        :param func_name: str
            name of the meta data function name
        :param func: callable
            The callable function
        """
        func_dict = self._load_func_dict()
        func_dict[func_name] = func
        with open(self.file_path, 'wb') as f:
            pickle.dump(func_dict, f)

    def _forward_transfer(self, x: np.ndarray) -> np.ndarray:
        raise NotImplementedError

    def _backward_transfer(self, x: np.ndarray) -> np.ndarray:
        raise NotImplementedError

    def _forward_derivative(self, x: np.ndarray) -> np.ndarray:
        raise NotImplementedError

    def _set_param(self, alpha: float):
        raise NotImplementedError

    def form_interpolator(self, theta_grid: np.ndarray, method: str,
                          param_known: Iterable[float], values_known: Iterable[float],
                          symmetrize=False, df: int = 5, s=1.1):
        """
        Forms the interpolator

        Since we are not able to derive the exact return values of certain parameters given a copula,
        what we do is generate a set of these values first, fit a spline and henceforth, interpolate the
        new values given

        :param theta_grid: ndarray
            original parameter grid
        :param method: str
            whether to use kendall tau or spearman rho for correlation calculation
        :param param_known: float iterable
            known parameters for copula
        :param values_known: float iterable
            known values given parameters for copula
        :param symmetrize: bool, default True
            if True, will make parameter grid symmetric
        :param df: int, default 5
            degree of freedom for smoothing spline. 1 <= df <= 5
        :param s: float, default 1.1
            smoothing constant for spline

        :return: Univariate Spline Model
        """

        method = method.lower()
        if method not in ('spearman', 'kendall'):
            raise ValueError('method must be one of (spearman, kendall)')

        alpha_grid = self._backward_transfer(theta_grid)
        grid = self._get_grid(alpha_grid, method)

        if symmetrize:
            grid = np.sign(theta_grid) * np.abs(grid) + np.abs(grid[::-1]) / 2

        good = ~np.isin(theta_grid, param_known)  # check for non-boundary cases (which are defined in param known)
        param = np.concatenate((param_known, theta_grid[good]))

        values_known = np.array(values_known)
        values = np.concatenate((values_known, grid[good]))
        w = np.concatenate((np.repeat(999, len(values_known)), np.ones(np.sum(good))))  # spline weights

        # spline needs to be sorted on 'x' data
        sort_index = param.argsort()
        param = param[sort_index]
        values = values[sort_index]
        w = w[sort_index]

        df = max(1, min(int(df), 5))
        return UnivariateSpline(param, values, w, k=df, s=s)

    def _get_grid(self, alpha_grid, method: str):
        results = np.empty_like(alpha_grid, float)
        for i, alpha in enumerate(alpha_grid):
            self._set_param(alpha)
            results[i] = tau_rho_sample(self.copula, self.nsim, method)

        return results


def tau_rho_sample(copula: BaseCopula, nsim: int, method="spearman") -> float:
    u = copula.random(nsim)
    u = u[~np.isnan(u).any(1)]

    return corr(u, method=method)[0, 1]
