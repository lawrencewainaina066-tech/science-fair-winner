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

def independent_t_test(group_a, group_b, equal_var=False):
    a = pd.to_numeric(pd.Series(group_a), errors="coerce").dropna().to_numpy()
    b = pd.to_numeric(pd.Series(group_b), errors="coerce").dropna().to_numpy()
    if len(a) < 2 or len(b) < 2:
        raise ValueError("Each group needs at least two valid numeric observations.")
    result = stats.ttest_ind(a, b, equal_var=equal_var, nan_policy="omit")
    return {"n_a": len(a), "n_b": len(b), "mean_a": float(np.mean(a)),
            "mean_b": float(np.mean(b)), "t_statistic": float(result.statistic),
            "p_value": float(result.pvalue), "test": "Welch independent-samples t-test" if not equal_var else "Independent-samples t-test"}

def paired_t_test(before, after):
    a = pd.to_numeric(pd.Series(before), errors="coerce")
    b = pd.to_numeric(pd.Series(after), errors="coerce")
    pairs = pd.concat([a, b], axis=1).dropna()
    if len(pairs) < 2:
        raise ValueError("At least two complete paired observations are required.")
    result = stats.ttest_rel(pairs.iloc[:, 0], pairs.iloc[:, 1])
    return {"n_pairs": len(pairs), "mean_before": float(pairs.iloc[:,0].mean()),
            "mean_after": float(pairs.iloc[:,1].mean()), "t_statistic": float(result.statistic),
            "p_value": float(result.pvalue), "test": "Paired-samples t-test"}

def chi_square_test(contingency):
    arr = np.asarray(contingency, dtype=float)
    if arr.ndim != 2 or min(arr.shape) < 2 or (arr < 0).any():
        raise ValueError("Provide a non-negative contingency table with at least 2 rows and 2 columns.")
    chi2, p, dof, expected = stats.chi2_contingency(arr)
    return {"chi_square": float(chi2), "p_value": float(p), "degrees_of_freedom": int(dof), "expected": expected}

def linear_regression(df, x_col, y_col):
    data = df[[x_col, y_col]].apply(pd.to_numeric, errors="coerce").dropna()
    if len(data) < 3:
        raise ValueError("At least three complete observations are required.")
    result = stats.linregress(data[x_col], data[y_col])
    return {"slope": float(result.slope), "intercept": float(result.intercept),
            "r_value": float(result.rvalue), "r_squared": float(result.rvalue**2),
            "p_value": float(result.pvalue), "n": len(data),
            "data": data, "x_label": x_col, "y_label": y_col}

def interpret_p_value(p, alpha=0.05):
    if p < alpha:
        return f"The p-value ({p:.4g}) is below alpha ({alpha:g}). The result is statistically significant under this test's assumptions. This does not by itself establish causation or practical importance."
    return f"The p-value ({p:.4g}) is not below alpha ({alpha:g}). The analysis does not provide sufficient evidence to reject the null hypothesis. This does not prove that there is no effect."
