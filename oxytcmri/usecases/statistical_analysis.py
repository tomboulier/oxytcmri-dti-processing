import dataclasses
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Tuple, Any

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from prettytable import PrettyTable
from scipy.stats import mannwhitneyu, fisher_exact
from statsmodels.discrete.discrete_model import Logit
import seaborn as sns
from statannotations.Annotator import Annotator


@dataclass
class MultivariateLogisticRegressionAnalysisResults:
    significant_variables_in_univariate_analysis: List[str] = dataclasses.field(default_factory=list)
    univariate_p_values: Dict[str, float] = dataclasses.field(default_factory=dict)
    odds_ratios: Dict[str, float] = dataclasses.field(default_factory=dict)
    confidence_intervals: Dict[str, Tuple] = dataclasses.field(default_factory=dict)
    final_model_variables: List[str] = dataclasses.field(default_factory=list)
    final_best_aic: float = None
    final_model: Any = None

    def univariate_analysis_results_to_string(self) -> str:
        # Round the odds ratios and p-values
        odds_ratios_rounded = {k: round(v, 2) for k, v in self.odds_ratios.items()}
        p_values_rounded = {k: round(v, 2) for k, v in self.univariate_p_values.items()}

        # Round the confidence intervals
        confidence_intervals_rounded = {k: (round(v[0], 2), round(v[1], 2)) for k, v in
                                        self.confidence_intervals.items()}

        data = {
            'Odds Ratio': odds_ratios_rounded,
            '95% Confidence Interval': confidence_intervals_rounded,
            'p-value': p_values_rounded
        }
        df = pd.DataFrame(data)
        return df.to_string()

    def multivariate_analysis_results_to_string(self) -> str:
        # Get the parameters, p-values, and confidence intervals from the final model
        params = self.final_model.params
        p_values = self.final_model.pvalues
        conf_int = self.final_model.conf_int()

        # Calculate the odds ratios
        odds_ratios = np.exp(params)

        # Calculate the confidence intervals for the odds ratios
        confidence_intervals = np.exp(conf_int)

        # Round the odds ratios, p-values, and confidence intervals to 2 decimal places
        odds_ratios_rounded = odds_ratios.round(2)
        p_values_rounded = p_values.round(2)
        confidence_intervals_rounded = confidence_intervals.round(2)

        # Create a DataFrame with the odds ratios, confidence intervals, and p-values
        data = {
            'Odds Ratio': odds_ratios_rounded,
            '95% Confidence Interval': confidence_intervals_rounded.apply(lambda x: (x[0], x[1]), axis=1),
            'p-value': p_values_rounded
        }
        df = pd.DataFrame(data)

        return df.to_string()

    def __str__(self) -> str:
        return (f"Univariate Analysis Results:\n"
                f"============================\n"
                f"{self.univariate_analysis_results_to_string()}\n\n"
                f"Multivariate Analysis Results:\n"
                f"============================\n"
                f"{self.multivariate_analysis_results_to_string()}")


class MultivariateLogisticRegressionAnalyzer:
    def __init__(self,
                 data_frame: pd.DataFrame,
                 mandatory_variables: List[str],
                 independent_variables: List[str],
                 dependant_variable: str,
                 start_variable: str):
        self.data = data_frame
        self.mandatory_variables = mandatory_variables
        self.independent_variables = independent_variables
        self.dependant_variable = dependant_variable
        self.start_variable = start_variable
        self.results = MultivariateLogisticRegressionAnalysisResults()
        self.correlation_matrix = None

    def perform_analysis(self) -> MultivariateLogisticRegressionAnalysisResults:
        """
        Logistic regression, with clustering option
        """
        self.compute_correlation_matrix()

        self.perform_univariate_logistic_regression_and_save_results(self.start_variable)
        self.select_significant_variables_with_univariate_logistic_regression()
        self.perform_multivariate_analysis_with_forward_selection()

        return self.results

    def compute_correlation_matrix(self):
        # Calculate the correlation matrix for additional variables
        variables = self.mandatory_variables + self.independent_variables + [self.start_variable]
        correlation_matrix = self.data[variables].corr()
        self.correlation_matrix = correlation_matrix

    def export_correlation_matrix_to_excel(self):
        # Export the correlation matrix to an Excel file
        self.correlation_matrix.to_excel("correlation_matrix.xlsx", index=True)

    def multivariate_logistic_regression_analysis(self, additional_variables: List[str]):
        all_variables = self.mandatory_variables + additional_variables + [self.dependant_variable]
        data_filtered = self.data.dropna(subset=all_variables)

        # Ajouter une constante au DataFrame
        data_filtered = data_filtered.copy()
        data_filtered.loc[:, 'const'] = 1

        y = data_filtered['outcome'].map({'unfavorable': 1, 'favorable': 0})
        x = data_filtered[['const'] + additional_variables + self.mandatory_variables]

        try:
            model = Logit(y, x)
            results_fit = model.fit(cov_type='cluster', cov_kwds={'groups': data_filtered['center_id']}, disp=0)
            return results_fit

        except Exception as e:
            print(f"Error processing multivariate logistic regression analysis with variable(s):\n"
                  f" {additional_variables}: {e}")

    def select_significant_variables_with_univariate_logistic_regression(self):
        for additional_variable in self.independent_variables:
            self.perform_univariate_logistic_regression_and_save_results(additional_variable)

            if self.results.univariate_p_values[additional_variable] < 0.20:
                self.results.significant_variables_in_univariate_analysis.append(additional_variable)

    def perform_univariate_logistic_regression_and_save_results(self, additional_variable):
        results_fit = self.multivariate_logistic_regression_analysis([additional_variable])
        pvalue_additional_variable = results_fit.pvalues[additional_variable]
        self.results.univariate_p_values[additional_variable] = pvalue_additional_variable
        odds_ratio = np.exp(results_fit.params[additional_variable])
        self.results.odds_ratios[additional_variable] = odds_ratio
        confidence_interval = np.exp(results_fit.conf_int().loc[additional_variable])
        self.results.confidence_intervals[additional_variable] = tuple(confidence_interval)

    def perform_multivariate_analysis_with_forward_selection(self) -> None:
        model_variables = [self.start_variable]
        variables_to_be_tested = self.independent_variables
        best_aic = self.multivariate_logistic_regression_analysis(model_variables).aic
        best_model = None

        continue_stepwise_selection = True

        while continue_stepwise_selection:
            min_aic, best_variable, model = self.aic_step(model_variables, best_aic, variables_to_be_tested)

            if min_aic < best_aic:
                best_aic = min_aic
                model_variables = model_variables + [best_variable]
                variables_to_be_tested.remove(best_variable)
                best_model = model
                continue_stepwise_selection = True

            else:
                continue_stepwise_selection = False
                self.results.final_model_variables = model_variables
                self.results.final_best_aic = best_aic
                self.results.final_model = best_model

    def aic_step(self, model_variables, best_aic, variables_to_be_tested):
        best_variable = ""
        best_model = None

        for variable in variables_to_be_tested:
            results_fit = self.multivariate_logistic_regression_analysis(model_variables + [variable])
            new_aic = results_fit.aic
            pvalue = results_fit.pvalues[variable]

            if new_aic < best_aic and pvalue < 0.20:
                best_aic = new_aic
                best_variable = variable
                best_model = results_fit

        return best_aic, best_variable, best_model


@dataclass
class OxyTCResults:
    data_frame = pd.DataFrame()

    def to_dataframe(self) -> pd.DataFrame:
        return self.data_frame

    def preprocess_data(self, analysis_population: str = "ITT") -> None:
        self.filter_population_analysis(population=analysis_population)
        self.add_neurological_outcome()
        self.add_sum_MD_lesions()
        self.add_bilaterality_index()
        self.drop_missing_data()
        self.binarize_variables()

    def filter_population_analysis(self, population: str = "ITT") -> None:
        """
        Filter the data frame for the population analysis:
        - ITT for "Intention To Treat"
        - mITT for "modified Intention To Treat"
        - PP for "Per Protocol"
        These populations are in increasning order of stringency, meaning that the PP population is a subset of the mITT,
        and the mITT is a subset of the ITT.
        Therefore, in the dataframe, the "analysis_population" column is encoded as follows:
        - "PP" for the Per Protocol population
        - "mITT" for the modified Intention To Treat population (and thus also the Per Protocol population)
        - "ITT" for the Intention To Treat population (and thus also the modified Intention To Treat and Per Protocol populations)
        """
        if population == "PP":
            self.data_frame = self.data_frame[self.data_frame["analysis_population"] == "PP"]
        elif population == "mITT":
            # we have to take PP and mITT
            self.data_frame = self.data_frame[self.data_frame["analysis_population"].isin(["PP", "mITT"])]
        elif population == "ITT":
            # we have to take PP, mITT and ITT
            self.data_frame = self.data_frame[self.data_frame["analysis_population"].isin(["PP", "mITT", "ITT"])]
        else:
            raise ValueError(f"Invalid population '{population}'. Possible values are 'ITT', 'mITT', and 'PP'.")

    def add_neurological_outcome(self) -> None:
        self.data_frame["outcome"] = ["unfavorable" if (x < 5) else "favorable" for x in
                                      self.data_frame["gose_6_months"]]
        self.data_frame["unfavorable_outcome"] = self.data_frame['outcome'].map({'unfavorable': 1, 'favorable': 0})

    def add_sum_MD_lesions(self) -> None:
        for quantile in ["_7_94", "_10_95"]:
            for localisation in ["_whole_brain",
                                 "_left_hemisphere",
                                 "_right_hemisphere",
                                 "_thalami",
                                 "_corpus_callosum",
                                 "_cerebral_white_matter"]:
                self.data_frame["sum_MD_lesions_in_mL" + quantile + localisation] = \
                    self.data_frame["high_MD_lesions_in_mL" + quantile + localisation] + \
                    self.data_frame["low_MD_lesions_in_mL" + quantile + localisation]

    def drop_missing_data(self):
        self.drop_missing_neurological_outcomes()
        self.drop_missing_mri_data()

    def drop_missing_neurological_outcomes(self, verbose: bool = False) -> None:
        if verbose:
            missing_gose_6_months_list = list(self.data_frame[self.data_frame["gose_6_months"].isna()]["subject_id"])
            print(f'There are {len(missing_gose_6_months_list)} patients with missing 6 months GOS-E: '
                  f'{missing_gose_6_months_list}')

        self.data_frame = self.data_frame[self.data_frame["gose_6_months"].notna()]

    def drop_missing_mri_data(self, verbose: bool = False) -> None:
        if verbose:
            missing_MD_lesions_list = list(
                self.data_frame[self.data_frame["low_MD_lesions_in_mL_7_94_whole_brain"].isna()]["subject_id"])
            print(f'There are {len(missing_MD_lesions_list)} patients with missing MD lesions: '
                  f'{missing_MD_lesions_list}')

        self.data_frame = self.data_frame[self.data_frame["low_MD_lesions_in_mL_7_94_whole_brain"].notna()]

    def add_bilaterality_index(self):
        for quantiles in ["7_94", "10_95"]:
            self.data_frame[f"bilaterality_index_{quantiles}"] = 1 - \
                                                                 abs(self.data_frame[
                                                                         f"sum_MD_lesions_in_mL_{quantiles}_left_hemisphere"] - \
                                                                     self.data_frame[
                                                                         f"sum_MD_lesions_in_mL_{quantiles}_right_hemisphere"]) \
                                                                 / self.data_frame[
                                                                     f"sum_MD_lesions_in_mL_{quantiles}_whole_brain"]

    def binarize_variables(self):
        self.data_frame['is_male'] = self.data_frame['sex'].map({'M': 1, 'F': 0})
        self.data_frame['trait_niv_3_r'] = self.data_frame['trait_niv_3_r'].map({'Oui': 1, 'Non': 0})
        self.data_frame['pupil_abnormality'] = self.data_frame['bl_reac_pupill_r'].apply(
            lambda x: 1 if x in [1.0, 0.0] else 0 if pd.notna(x) else x
        )

    def get_values(self, column_name: str) -> list:
        """
        Get the values of a specific column in the data frame.

        Args:
        -----
            column_name (str): The name of the column to get the values from.

        Returns:
        --------
            list: A list of values from the specified column.
        """
        try:
            values = self.data_frame[column_name].to_list()
        except KeyError:
            raise KeyError(f"The column '{column_name}' is not available in the data frame.")
        return values

    def get_pbto2_values(self) -> list[bool]:
        """
        Get the pbtO2 values for the subjects.

        Returns:
        --------
            list[bool]: A list of boolean values indicating whether the pbtO2 values are available for each subject.
        """
        return self.get_values("pbto2")

    def get_values_by_treatment_group(self, variable: str, group: str) -> list[int]:
        """
        Get the age values for the subjects in the specified group.

        Parameters:
        -----------
            variable (str): The variable to get values from.
            group (str): The group to get the age values from. Possible values are "pbto2" and "icp_only".

        Returns:
        --------
            list[int]: A list of age values for the subjects in the specified group.
        """
        variable_values = np.array(self.get_values(variable))
        pbto2_values = np.array(self.get_pbto2_values())
        if group == "pbto2":
            results = variable_values[pbto2_values].tolist()
            # filter out missing values
            return [x for x in results if not pd.isna(x)]
        elif group == "icp_only":
            results = variable_values[~pbto2_values].tolist()
            # filter out missing values
            return [x for x in results if not pd.isna(x)]
        else:
            raise ValueError(f"Invalid group '{group}'. Possible values are 'pbto2' and 'icp_only'.")


class OxyTCResultsBuilder:
    def __init__(self, analysis_population: str = "ITT"):
        self.oxy_tc_results = OxyTCResults()
        self.analysis_population = analysis_population

    def from_csv(self, csv_filename: str) -> OxyTCResults:
        self.oxy_tc_results.data_frame = pd.read_csv(csv_filename)
        self.oxy_tc_results.preprocess_data(analysis_population=self.analysis_population)

        return self.oxy_tc_results


class StatisticsEstimates(ABC):
    @abstractmethod
    def to_string(self) -> str:
        pass


@dataclass
class MedianIQR(StatisticsEstimates):
    median: float
    iqr_lower: float
    iqr_upper: float

    def to_string(self):
        return f"{self.median:.2f} ({self.iqr_lower:.2f}-{self.iqr_upper:.2f})"


@dataclass
class CountPercentage(StatisticsEstimates):
    count: int
    total: int

    def to_string(self) -> str:
        percentage = (self.count / self.total) * 100
        return f"{self.count}/{self.total} ({percentage:.2f}%)"


@dataclass()
class GroupStatistics:
    """
    A class to represent the statistics for a group of subjects.
    """
    pbto2_estimates: StatisticsEstimates
    icp_only_estimates: StatisticsEstimates
    p_value: float


class StatisticsExtractor:
    def __init__(self, oxytc_results: OxyTCResults):
        self.oxytc_results = oxytc_results

    def get_group_counts(self) -> Tuple[int, int]:
        """
        Get the number of subjects in each group.

        Returns:
        --------
            Tuple[int, int]: The number of subjects in each group
        """
        pbto2_values = self.oxytc_results.get_pbto2_values()
        return pbto2_values.count(False), pbto2_values.count(True)

    def get_group_statistics(self, variable: str, estimator_type: type, default_value: Any = None) -> GroupStatistics:
        """
        Get the statistics for the specified variable in each group.

        Parameters
        ----------
            variable (str): The variable to get the statistics for.
            estimator_type (type): The type of estimator to use for computing the statistics.
                                   Possible values are MedianIQR and CountPercentage.
        Returns
        -------
            GroupStatistics: The statistics for the specified variable in each group.
        """
        # Get the age values for each group
        values_in_pbto2_group = self.oxytc_results.get_values_by_treatment_group(variable=variable, group="pbto2")
        values_in_icp_only_group = self.oxytc_results.get_values_by_treatment_group(variable=variable, group="icp_only")

        if estimator_type == MedianIQR:
            return GroupStatistics(
                pbto2_estimates=self.get_median_iqr(variable=variable, group="pbto2"),
                icp_only_estimates=self.get_median_iqr(variable=variable, group="icp_only"),
                p_value=self.compute_p_value(variable=variable, test="mannwhitneyu")
            )
        elif estimator_type == CountPercentage:
            if default_value is None:
                raise ValueError("A default value must be provided when using the CountPercentage estimator_type.")
            return GroupStatistics(
                pbto2_estimates=self.get_count_percentage(variable=variable, default_value=default_value,
                                                          group="pbto2"),
                icp_only_estimates=self.get_count_percentage(variable=variable, default_value=default_value,
                                                             group="icp_only"),
                p_value=self.compute_p_value(variable=variable, test="fisher_exact", default_value=default_value)
            )
        else:
            raise ValueError(f"Invalid estimator_type '{estimator_type}'. Possible values are 'MedianIQR'.")

    def get_median_iqr(self, variable: str, group: str):
        """
        Get the median and IQR of the age values for the specified group.

        Parameters:
        -----------
            variable (str): The variable to get the statistics for.
            group (str): The group to get the statistics for. Possible values are "pbto2" and "icp_only".

        Returns:
        --------
            MedianIQR: The median and IQR of the age values for the specified group.
        """
        values = self.oxytc_results.get_values_by_treatment_group(variable=variable, group=group)
        median = float(np.median(values))
        iqr_lower, iqr_upper = np.percentile(values, [25, 75])
        return MedianIQR(median=median, iqr_lower=iqr_lower, iqr_upper=iqr_upper)

    def get_count_percentage(self, variable: str, default_value: Any, group: str):
        """
        Get the count and percentage of the subjects in the specified group.

        Parameters:
        -----------
            variable (str): The variable to get the statistics for.
            group (str): The group to get the statistics for. Possible values are "pbto2" and "icp_only".

        Returns:
        --------
            CountPercentage: The count and percentage of the subjects in the specified group.
        """
        values = self.oxytc_results.get_values_by_treatment_group(variable=variable, group=group)
        values_equals_to_default = [value == default_value for value in values]
        count = values_equals_to_default.count(True)
        total = len(values)
        return CountPercentage(count=count, total=total)

    def compute_p_value(self, variable: str, test: str, default_value: Any = None) -> float:
        """
        Compute the p-value for the specified test.

        Parameters:
        -----------
            variable (str): The variable to compute the p-value for.
            test (str): The test to use for computing the p-value.
                        Possible values are "mannwhitneyu" and "fisher_exact".

        Returns:
        --------
            float: The p-value for the specified test.
        """
        if test == "mannwhitneyu":
            values_in_pbto2_group = self.oxytc_results.get_values_by_treatment_group(variable=variable, group="pbto2")
            values_in_icp_only_group = self.oxytc_results.get_values_by_treatment_group(variable=variable,
                                                                                        group="icp_only")
            _, p_value = mannwhitneyu(values_in_pbto2_group, values_in_icp_only_group)
            return p_value
        elif test == "fisher_exact":
            if default_value is None:
                raise ValueError("A default value must be provided when using the Fisher exact test.")
            values_in_pbto2_group = self.oxytc_results.get_values_by_treatment_group(variable=variable, group="pbto2")
            values_in_icp_only_group = self.oxytc_results.get_values_by_treatment_group(variable=variable,
                                                                                        group="icp_only")
            count_pbto2 = values_in_pbto2_group.count(default_value)
            count_icp_only = values_in_icp_only_group.count(default_value)
            test_result = fisher_exact([[count_pbto2, len(values_in_pbto2_group) - count_pbto2],
                                        [count_icp_only, len(values_in_icp_only_group) - count_icp_only]])
            return float(test_result.pvalue)
        else:
            raise ValueError(f"Invalid test '{test}'. Possible values are 'mannwhitneyu' and 'fisher_exact'.")


class BaseLineCharacteristicsTable:
    def __init__(self, oxytc_results: OxyTCResults):
        self.oxytc_results = oxytc_results
        self.stats_extractor = StatisticsExtractor(oxytc_results)

    def __str__(self) -> str:
        results = "Baseline Characteristics Table" + "\n"
        results += "==============================" + "\n"

        # Create a pretty table
        table_to_print = PrettyTable(["", "Intracranial pressure only", "Intracranial pressure and PbtO2", "p-value"])

        # Add rows dynamically
        for row in self.get_baseline_characteristics():
            table_to_print.add_row(row)

        results += str(table_to_print)

        return results

    @staticmethod
    def get_row(variable_display_name: str, group_stats: GroupStatistics) -> Tuple:
        """
        Get a row of the baseline characteristics table.

        Parameters:
        -----------
            group_stats (GroupStatistics): The statistics for the group.

        Returns:
        --------
            Tuple: A tuple containing the baseline characteristics of the subjects.
        """
        return (variable_display_name,
                group_stats.icp_only_estimates.to_string(),
                group_stats.pbto2_estimates.to_string(),
                f"{group_stats.p_value:.2f}")

    def get_baseline_characteristics(self):
        """
        Get the baseline characteristics of the subjects.

        Returns:
        --------
            List[Tuple]: A list of tuples containing the baseline characteristics of the subjects
        """
        group_counts = self.stats_extractor.get_group_counts()
        data = [
            ("N", group_counts[0], group_counts[1], ""),
            self.get_row("Age (years)",
                         self.stats_extractor.get_group_statistics(variable="age", estimator_type=MedianIQR)),
            self.get_row("Male sex",
                         self.stats_extractor.get_group_statistics(variable="sex",
                                                                   estimator_type=CountPercentage,
                                                                   default_value="M")),
            self.get_row("IMPACT score (neurological outcome)",
                         self.stats_extractor.get_group_statistics(variable="impact_score_mortality",
                                                                   estimator_type=MedianIQR)),
            self.get_row("Glasgow score",
                         self.stats_extractor.get_group_statistics(variable="glasgow_coma_scale",
                                                                   estimator_type=MedianIQR)),
            self.get_row("Normal pupil reactivity",
                         self.stats_extractor.get_group_statistics(variable="bl_reac_pupill_r",
                                                                   estimator_type=CountPercentage,
                                                                   default_value=2)),
            self.get_row("MARSHALL score",
                         self.stats_extractor.get_group_statistics(variable="marshall_score",
                                                                   estimator_type=MedianIQR)),
            self.get_row("SAPS score",
                         self.stats_extractor.get_group_statistics(variable="IGS2",
                                                                   estimator_type=MedianIQR)),
            self.get_row("Intracranial pressure on ICU admission (mmHg)",
                         self.stats_extractor.get_group_statistics(variable="PIC_H0",
                                                                   estimator_type=MedianIQR)),
            self.get_row("Mean arterial blood pressure on ICU admission (mmHg)",
                         self.stats_extractor.get_group_statistics(variable="PAM_H0",
                                                                   estimator_type=MedianIQR)),
            self.get_row("Cerebral perfusion pressure on ICU admission (mmHg)",
                         self.stats_extractor.get_group_statistics(variable="PPC_H0",
                                                                   estimator_type=MedianIQR)),
        ]
        return data

    def to_excel(self, statistics_excel_output_path: str) -> None:
        """
        Export the baseline characteristics table to an Excel file.

        Parameters:
        -----------
            statistics_excel_output_path (str): The path to the Excel file to export the table to.

        Returns:
        --------
            None
        """
        # Create a DataFrame with the baseline characteristics
        data = self.get_baseline_characteristics()
        df = pd.DataFrame(data,
                          columns=["", "Intracranial pressure only", "Intracranial pressure and PbtO2", "p-value"])

        # Export the DataFrame to an Excel file, in a sheet named "Baseline Characteristics"
        df.to_excel(statistics_excel_output_path, index=False, sheet_name="Baseline Characteristics")


class OutcomesGraph:
    def __init__(self, oxytc_results: OxyTCResults):
        self.oxytc_results = oxytc_results
        self.stats_extractor = StatisticsExtractor(oxytc_results)
        self.variable_groups = ["pbto2"]

    def get_legend_elements(self, variable_group="pbto2"):
        if variable_group == "pbto2":
            return {
                "labels": ["ICP only", "ICP + PbtO2"],
                "title": "Treatment Group",
            }
        elif variable_group == "gose":
            raise NotImplementedError("Legend elements for the GOSE variable group are not implemented yet.")
        else:
            raise ValueError(f"Invalid variable group '{variable_group}'. Possible values are 'pbto2' and 'gose'.")

    def prepare_graph(self, variable_group="pbto2"):
        # Preparing data
        data = self.oxytc_results.data_frame.melt(id_vars=['subject_id', variable_group],
                                                  value_vars=['sum_MD_lesions_in_mL_7_94_whole_brain',
                                                              'high_MD_lesions_in_mL_7_94_whole_brain',
                                                              'low_MD_lesions_in_mL_7_94_whole_brain'])

        # Plot parameters
        plot_params = {
            'data': data,
            'x': 'variable',
            'y': 'value',
            "hue": variable_group,
        }

        plt.figure(figsize=(10, 6))
        ax = sns.boxplot(**plot_params)
        plt.ylabel('Volume of MD lesions (in mL)')
        plt.xlabel('')
        ax.set_xlabel("")
        ax.set_xticks([0, 1, 2])
        ax.set_xticklabels(["Sum of regions (high+low)", "High MD regions", "Low MD regions"])

        # Customize legend
        legend_elements = self.get_legend_elements(variable_group)
        handles, labels = ax.get_legend_handles_labels()
        ax.legend(handles, legend_elements['labels'], title=legend_elements['title'], loc='upper right', frameon=True)

        # Annotate plot
        pairs = [
            [('sum_MD_lesions_in_mL_7_94_whole_brain', False), ('sum_MD_lesions_in_mL_7_94_whole_brain', True)],
            [('high_MD_lesions_in_mL_7_94_whole_brain', False), ('high_MD_lesions_in_mL_7_94_whole_brain', True)],
            [('low_MD_lesions_in_mL_7_94_whole_brain', False), ('low_MD_lesions_in_mL_7_94_whole_brain', True)],
        ]
        annotator = Annotator(ax, pairs, **plot_params)
        annotator.configure(test="t-test_ind").apply_and_annotate()

    def to_svg(self, outcomes_graph_svg_output_path: str) -> None:
        """
        Export the outcomes graph to an SVG file.

        Parameters:
        -----------
            outcomes_graph_svg_output_path (str): The path to the SVG file to export the graph to.

        Returns:
        --------
            None
        """
        for variable_group in self.variable_groups:
            self.prepare_graph(variable_group)
            file_name_without_extension = outcomes_graph_svg_output_path.split(".")[0]
            file_name = f"{file_name_without_extension}_{variable_group}.svg"
            plt.savefig(file_name, format="svg")

    def plot(self):
        for variable_group in self.variable_groups:
            self.prepare_graph(variable_group)
            # Show plot
            plt.show()
