import numpy as np
import pandas as pd
from scipy import stats

def load_table(uploaded_file):
    name = uploaded_file.name.lower()
    if name.endswith(".csv"):
        return pd.read_csv(uploaded_file)
    if name.endswith((".xlsx", ".xls")):
        return pd.read_excel(uploaded_file)
    raise ValueError("Upload a CSV or Excel file.")

def numeric_summary(df):
    numeric = df.select_dtypes(include="number")
    if numeric.empty:
        return pd.DataFrame()
    return numeric.describe().T

def correlation_matrix(df):
    numeric = df.select_dtypes(include="number")
    if numeric.shape[1] < 2:
        raise ValueError("At least two numeric columns are required.")
    return numeric.corr(numeric_only=True)

def independent_t_test(group_a, group_b, equal_var=False, alpha=0.05):
    a = pd.to_numeric(pd.Series(group_a), errors="coerce").dropna().to_numpy()
    b = pd.to_numeric(pd.Series(group_b), errors="coerce").dropna().to_numpy()
    if not 0 < alpha < 1:
        raise ValueError("Alpha must be between 0 and 1.")
    a = a[np.isfinite(a)]
    b = b[np.isfinite(b)]
    if len(a) < 2 or len(b) < 2:
        raise ValueError("Each group needs at least two valid finite numeric observations.")
    result = stats.ttest_ind(a, b, equal_var=equal_var, nan_policy="omit")
    mean_a, mean_b = float(np.mean(a)), float(np.mean(b))
    var_a, var_b = float(np.var(a, ddof=1)), float(np.var(b, ddof=1))
    difference = mean_a - mean_b
    if equal_var:
        dfree = len(a) + len(b) - 2
        pooled_var = ((len(a) - 1) * var_a + (len(b) - 1) * var_b) / dfree
        standard_error = float(np.sqrt(pooled_var * (1 / len(a) + 1 / len(b))))
    else:
        va, vb = var_a / len(a), var_b / len(b)
        standard_error = float(np.sqrt(va + vb))
        denominator = va ** 2 / (len(a) - 1) + vb ** 2 / (len(b) - 1)
        dfree = float((va + vb) ** 2 / denominator) if denominator else float("nan")
    if standard_error > 0 and np.isfinite(dfree):
        margin = float(stats.t.ppf(1 - alpha / 2, dfree) * standard_error)
        confidence_interval = [difference - margin, difference + margin]
    else:
        confidence_interval = [float("nan"), float("nan")]
    pooled_sd = float(np.sqrt(((len(a)-1)*var_a + (len(b)-1)*var_b) /
                              (len(a)+len(b)-2)))
    cohens_d = difference / pooled_sd if pooled_sd > 0 else None
    return {
        "n_a": len(a), "n_b": len(b), "mean_a": mean_a, "mean_b": mean_b,
        "mean_difference_a_minus_b": difference,
        "confidence_level": 1 - alpha, "mean_difference_ci": confidence_interval,
        "t_statistic": float(result.statistic), "p_value": float(result.pvalue),
        "degrees_of_freedom": float(result.df) if hasattr(result, "df") else float(dfree),
        "cohens_d": float(cohens_d) if cohens_d is not None else None,
        "test": "Welch independent-samples t-test" if not equal_var else "Pooled independent-samples t-test",
    }

def paired_t_test(before, after, alpha=0.05):
    if not 0 < alpha < 1:
        raise ValueError("Alpha must be between 0 and 1.")
    a = pd.to_numeric(pd.Series(before), errors="coerce")
    b = pd.to_numeric(pd.Series(after), errors="coerce")
    pairs = pd.concat([a, b], axis=1).replace([np.inf, -np.inf], np.nan).dropna()
    if len(pairs) < 2:
        raise ValueError("At least two complete finite paired observations are required.")
    differences = (pairs.iloc[:, 1] - pairs.iloc[:, 0]).to_numpy(dtype=float)
    result = stats.ttest_rel(pairs.iloc[:, 1], pairs.iloc[:, 0])
    mean_difference = float(np.mean(differences))
    sd_difference = float(np.std(differences, ddof=1))
    standard_error = sd_difference / np.sqrt(len(differences))
    if standard_error > 0:
        margin = float(stats.t.ppf(1 - alpha / 2, len(differences) - 1) * standard_error)
        confidence_interval = [mean_difference - margin, mean_difference + margin]
    else:
        confidence_interval = [mean_difference, mean_difference]
    cohens_dz = mean_difference / sd_difference if sd_difference > 0 else None
    return {
        "n_pairs": len(pairs),
        "mean_before": float(pairs.iloc[:, 0].mean()),
        "mean_after": float(pairs.iloc[:, 1].mean()),
        "mean_difference_after_minus_before": mean_difference,
        "confidence_level": 1 - alpha, "mean_difference_ci": confidence_interval,
        "t_statistic": float(result.statistic), "p_value": float(result.pvalue),
        "cohens_dz": float(cohens_dz) if cohens_dz is not None else None,
        "test": "Paired-samples t-test",
    }

def chi_square_test(contingency):
    arr = np.asarray(contingency, dtype=float)
    if arr.ndim != 2 or min(arr.shape) < 2 or not np.isfinite(arr).all() or (arr < 0).any():
        raise ValueError("Provide a finite, non-negative contingency table with at least 2 rows and 2 columns.")
    if np.any(arr.sum(axis=0) == 0) or np.any(arr.sum(axis=1) == 0):
        raise ValueError("Every row and column must have a positive total.")
    chi2, p, dof, expected = stats.chi2_contingency(arr)
    return {
        "chi_square": float(chi2), "p_value": float(p),
        "degrees_of_freedom": int(dof), "expected": expected.tolist(),
        "minimum_expected_frequency": float(expected.min()),
        "small_expected_frequency_warning": bool((expected < 5).any()),
    }

def linear_regression(df, x_col, y_col):
    data = df[[x_col, y_col]].apply(pd.to_numeric, errors="coerce").dropna()
    data = data.replace([np.inf, -np.inf], np.nan).dropna()
    if x_col == y_col:
        raise ValueError("Choose different predictor (X) and outcome (Y) columns.")
    if len(data) < 3:
        raise ValueError("At least three complete finite observations are required.")
    if data[x_col].nunique() < 2:
        raise ValueError("The predictor must contain at least two distinct values.")
    result = stats.linregress(data[x_col], data[y_col])
    return {"slope": float(result.slope), "intercept": float(result.intercept),
            "r_value": float(result.rvalue), "r_squared": float(result.rvalue**2),
            "p_value": float(result.pvalue), "slope_standard_error": float(result.stderr), "n": len(data),
            "data": data, "x_label": x_col, "y_label": y_col}

def interpret_p_value(p, alpha=0.05):
    if not np.isfinite(p) or not 0 <= p <= 1:
        raise ValueError("The p-value must be a finite number between 0 and 1.")
    if not np.isfinite(alpha) or not 0 < alpha < 1:
        raise ValueError("Alpha must be a finite number between 0 and 1.")
    if p < alpha:
        return f"The p-value ({p:.4g}) is below alpha ({alpha:g}). The result is statistically significant under this test's assumptions. This does not by itself establish causation or practical importance."
    return f"The p-value ({p:.4g}) is not below alpha ({alpha:g}). The analysis does not provide sufficient evidence to reject the null hypothesis. This does not prove that there is no effect."
