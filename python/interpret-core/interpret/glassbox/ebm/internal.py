# Copyright (c) 2019 Microsoft Corporation
# Distributed under the MIT software license

# TODO: Add unit tests for internal EBM interfacing
import sys
from sys import platform
import ctypes as ct
from numpy.ctypeslib import ndpointer
import numpy as np
import os
import struct
import logging

from .utils import EBMUtils

log = logging.getLogger(__name__)

this = sys.modules[__name__]
this.native = None


class Native:
    """Layer/Class responsible for native function calls."""

    # enum FeatureType : int64_t
    # Ordinal = 0
    FeatureTypeOrdinal = 0
    # Nominal = 1
    FeatureTypeNominal = 1

    class EbmCoreFeature(ct.Structure):
        _fields_ = [
            # FeatureType featureType;
            ("featureType", ct.c_longlong),
            # bool hasMissing;
            ("hasMissing", ct.c_longlong),
            # int64_t countBins;
            ("countBins", ct.c_longlong),
        ]

    class EbmCoreFeatureCombination(ct.Structure):
        _fields_ = [
            # int64_t countFeaturesInCombination;
            ("countFeaturesInCombination", ct.c_longlong)
        ]

    # const signed char TraceLevelOff = 0;
    TraceLevelOff = 0
    # const signed char TraceLevelError = 1;
    TraceLevelError = 1
    # const signed char TraceLevelWarning = 2;
    TraceLevelWarning = 2
    # const signed char TraceLevelInfo = 3;
    TraceLevelInfo = 3
    # const signed char TraceLevelVerbose = 4;
    TraceLevelVerbose = 4

    LogFuncType = ct.CFUNCTYPE(None, ct.c_char, ct.c_char_p)

    def __init__(self, is_debug=False, log_level=None):
        self.is_debug = is_debug
        self.log_level = log_level

        self.lib = ct.cdll.LoadLibrary(self.get_ebm_lib_path(debug=is_debug))
        self.harden_function_signatures()
        self.set_logging(level=log_level)

    def harden_function_signatures(self):
        """ Adds types to function signatures. """
        self.lib.SetLogMessageFunction.argtypes = [
            # void (* fn)(signed char traceLevel, const char * message) logMessageFunction
            self.LogFuncType
        ]
        self.lib.SetTraceLevel.argtypes = [
            # signed char traceLevel
            ct.c_char
        ]

        self.lib.InitializeTrainingClassification.argtypes = [
            # int64_t randomSeed
            ct.c_longlong,
            # int64_t countFeatures
            ct.c_longlong,
            # EbmCoreFeature * features
            ct.POINTER(self.EbmCoreFeature),
            # int64_t countFeatureCombinations
            ct.c_longlong,
            # EbmCoreFeatureCombination * featureCombinations
            ct.POINTER(self.EbmCoreFeatureCombination),
            # int64_t * featureCombinationIndexes
            ndpointer(dtype=np.int64, ndim=1),
            # int64_t countTargetClasses
            ct.c_longlong,
            # int64_t countTrainingInstances
            ct.c_longlong,
            # int64_t * trainingTargets
            ndpointer(dtype=np.int64, ndim=1),
            # int64_t * trainingBinnedData
            ndpointer(dtype=np.int64, ndim=2, flags="F_CONTIGUOUS"),
            # double * trainingPredictorScores
            ndpointer(dtype=np.float64, ndim=1),
            # int64_t countValidationInstances
            ct.c_longlong,
            # int64_t * validationTargets
            ndpointer(dtype=np.int64, ndim=1),
            # int64_t * validationBinnedData
            ndpointer(dtype=np.int64, ndim=2, flags="F_CONTIGUOUS"),
            # double * validationPredictorScores
            ndpointer(dtype=np.float64, ndim=1),
            # int64_t countInnerBags
            ct.c_longlong,
        ]
        self.lib.InitializeTrainingClassification.restype = ct.c_void_p

        self.lib.InitializeTrainingRegression.argtypes = [
            # int64_t randomSeed
            ct.c_longlong,
            # int64_t countFeatures
            ct.c_longlong,
            # EbmCoreFeature * features
            ct.POINTER(self.EbmCoreFeature),
            # int64_t countFeatureCombinations
            ct.c_longlong,
            # EbmCoreFeatureCombination * featureCombinations
            ct.POINTER(self.EbmCoreFeatureCombination),
            # int64_t * featureCombinationIndexes
            ndpointer(dtype=np.int64, ndim=1),
            # int64_t countTrainingInstances
            ct.c_longlong,
            # double * trainingTargets
            ndpointer(dtype=np.float64, ndim=1),
            # int64_t * trainingBinnedData
            ndpointer(dtype=np.int64, ndim=2, flags="F_CONTIGUOUS"),
            # double * trainingPredictorScores
            ndpointer(dtype=np.float64, ndim=1),
            # int64_t countValidationInstances
            ct.c_longlong,
            # double * validationTargets
            ndpointer(dtype=np.float64, ndim=1),
            # int64_t * validationBinnedData
            ndpointer(dtype=np.int64, ndim=2, flags="F_CONTIGUOUS"),
            # double * validationPredictorScores
            ndpointer(dtype=np.float64, ndim=1),
            # int64_t countInnerBags
            ct.c_longlong,
        ]
        self.lib.InitializeTrainingRegression.restype = ct.c_void_p

        self.lib.GenerateModelFeatureCombinationUpdate.argtypes = [
            # void * ebmTraining
            ct.c_void_p,
            # int64_t indexFeatureCombination
            ct.c_longlong,
            # double learningRate
            ct.c_double,
            # int64_t countTreeSplitsMax
            ct.c_longlong,
            # int64_t countInstancesRequiredForParentSplitMin
            ct.c_longlong,
            # double * trainingWeights
            # ndpointer(dtype=np.float64, ndim=1),
            ct.c_void_p,
            # double * validationWeights
            # ndpointer(dtype=np.float64, ndim=1),
            ct.c_void_p,
            # double * gainReturn
            ct.POINTER(ct.c_double),
        ]
        self.lib.GenerateModelFeatureCombinationUpdate.restype = ct.POINTER(ct.c_double)

        self.lib.ApplyModelFeatureCombinationUpdate.argtypes = [
            # void * ebmTraining
            ct.c_void_p,
            # int64_t indexFeatureCombination
            ct.c_longlong,
            # double * modelFeatureCombinationUpdateTensor
            ct.POINTER(ct.c_double),
            # double * validationMetricReturn
            ct.POINTER(ct.c_double),
        ]
        self.lib.ApplyModelFeatureCombinationUpdate.restype = ct.c_longlong

        self.lib.GetCurrentModelFeatureCombination.argtypes = [
            # void * ebmTraining
            ct.c_void_p,
            # int64_t indexFeatureCombination
            ct.c_longlong,
        ]
        self.lib.GetCurrentModelFeatureCombination.restype = ct.POINTER(ct.c_double)

        self.lib.GetBestModelFeatureCombination.argtypes = [
            # void * ebmTraining
            ct.c_void_p,
            # int64_t indexFeatureCombination
            ct.c_longlong,
        ]
        self.lib.GetBestModelFeatureCombination.restype = ct.POINTER(ct.c_double)

        self.lib.FreeTraining.argtypes = [
            # void * ebmTraining
            ct.c_void_p
        ]

        self.lib.InitializeInteractionClassification.argtypes = [
            # int64_t countFeatures
            ct.c_longlong,
            # EbmCoreFeature * features
            ct.POINTER(self.EbmCoreFeature),
            # int64_t countTargetClasses
            ct.c_longlong,
            # int64_t countInstances
            ct.c_longlong,
            # int64_t * targets
            ndpointer(dtype=np.int64, ndim=1),
            # int64_t * binnedData
            ndpointer(dtype=np.int64, ndim=2, flags="F_CONTIGUOUS"),
            # double * predictorScores
            ndpointer(dtype=np.float64, ndim=1),
        ]
        self.lib.InitializeInteractionClassification.restype = ct.c_void_p

        self.lib.InitializeInteractionRegression.argtypes = [
            # int64_t countFeatures
            ct.c_longlong,
            # EbmCoreFeature * features
            ct.POINTER(self.EbmCoreFeature),
            # int64_t countInstances
            ct.c_longlong,
            # double * targets
            ndpointer(dtype=np.float64, ndim=1),
            # int64_t * binnedData
            ndpointer(dtype=np.int64, ndim=2, flags="F_CONTIGUOUS"),
            # double * predictorScores
            ndpointer(dtype=np.float64, ndim=1),
        ]
        self.lib.InitializeInteractionRegression.restype = ct.c_void_p

        self.lib.GetInteractionScore.argtypes = [
            # void * ebmInteraction
            ct.c_void_p,
            # int64_t countFeaturesInCombination
            ct.c_longlong,
            # int64_t * featureIndexes
            ndpointer(dtype=np.int64, ndim=1),
            # double * interactionScoreReturn
            ct.POINTER(ct.c_double),
        ]
        self.lib.GetInteractionScore.restype = ct.c_longlong

        self.lib.FreeInteraction.argtypes = [
            # void * ebmInteraction
            ct.c_void_p
        ]

    def set_logging(self, level=None):
        def native_log(trace_level, message):
            try:
                trace_level = int(trace_level[0])
                message = message.decode("ascii")

                if trace_level == self.TraceLevelError:
                    log.error(message)
                elif trace_level == self.TraceLevelWarning:
                    log.warning(message)
                elif trace_level == self.TraceLevelInfo:
                    log.info(message)
                elif trace_level == self.TraceLevelVerbose:
                    log.debug(message)
            except: # we're being called from C, so we can't raise exceptions
                pass

        if level is None:
            root = logging.getLogger("interpret")
            level = root.getEffectiveLevel()

        level_dict = {
            logging.DEBUG: self.TraceLevelVerbose,
            logging.INFO: self.TraceLevelInfo,
            logging.WARNING: self.TraceLevelWarning,
            logging.ERROR: self.TraceLevelError,
            logging.CRITICAL: self.TraceLevelError,
            logging.NOTSET: self.TraceLevelOff,
            "DEBUG": self.TraceLevelVerbose,
            "INFO": self.TraceLevelInfo,
            "WARNING": self.TraceLevelWarning,
            "ERROR": self.TraceLevelError,
            "CRITICAL": self.TraceLevelError,
            "NOTSET": self.TraceLevelOff,
        }

        self.typed_log_func = self.LogFuncType(native_log)
        self.lib.SetLogMessageFunction(self.typed_log_func)
        self.lib.SetTraceLevel(ct.c_char(level_dict[level]))

    def get_ebm_lib_path(self, debug=False):
        """ Returns filepath of core EBM library.

        Returns:
            A string representing filepath.
        """
        bitsize = struct.calcsize("P") * 8
        is_64_bit = bitsize == 64

        script_path = os.path.dirname(os.path.abspath(__file__))
        package_path = os.path.join(script_path, "..", "..")

        debug_str = "_debug" if debug else ""
        log.info("Loading native on {0} | debug = {1}".format(platform, debug))
        if platform == "linux" or platform == "linux2" and is_64_bit:
            return os.path.join(
                package_path, "lib", "lib_ebmcore_linux_x64{0}.so".format(debug_str)
            )
        elif platform == "win32" and is_64_bit:
            return os.path.join(
                package_path, "lib", "lib_ebmcore_win_x64{0}.dll".format(debug_str)
            )
        elif platform == "darwin" and is_64_bit:
            return os.path.join(
                package_path, "lib", "lib_ebmcore_mac_x64{0}.dylib".format(debug_str)
            )
        else:
            msg = "Platform {0} at {1} bit not supported for EBM".format(
                platform, bitsize
            )
            log.error(msg)
            raise Exception(msg)


class NativeEBM:
    """Lightweight wrapper for EBM C code.
    """

    def __init__(
        self,
        features,
        feature_combinations,
        X_train,
        y_train,
        X_val,
        y_val,
        model_type,
        num_inner_bags=0,
        num_classification_states=2,
        training_scores=None,
        validation_scores=None,
        random_state=1337,
    ):

        # TODO: Update documentation for training/val scores args.
        """ Initializes internal wrapper for EBM C code.

        Args:
            features: List of features represented individually as
                dictionary of keys ('type', 'has_missing', 'n_bins').
            feature_combinations: List of feature combinations represented as
                a dictionary of keys ('n_attributes', 'attributes')
            X_train: Training design matrix as 2-D ndarray.
            y_train: Training response as 1-D ndarray.
            X_val: Validation design matrix as 2-D ndarray.
            y_val: Validation response as 1-D ndarray.
            model_type: 'regression'/'classification'.
            num_inner_bags: Per feature training step, number of inner bags.
            num_classification_states: Specific to classification,
                number of unique classes.
            training_scores: Undocumented.
            validation_scores: Undocumented.
            random_state: Random seed as integer.
        """
        log.debug("Check if EBM lib is loaded")
        if this.native is None:
            log.info("EBM lib loading.")
            # TODO we need to thread protect this load.  It won't fail currently, but might load multiple times 
            this.native = Native()
        else:
            log.debug("EBM lib already loaded")

        log.info("Allocation start")

        # Store args
        self.features = features
        self.feature_combinations = feature_combinations
        self.feature_array, self.feature_combinations_array, self.feature_combination_indexes = self._convert_feature_info_to_c(
            features, feature_combinations
        )

        self.X_train = X_train
        self.y_train = y_train
        self.X_val = X_val
        self.y_val = y_val
        self.model_type = model_type
        self.num_inner_bags = num_inner_bags
        self.num_classification_states = num_classification_states

        self.training_scores = training_scores
        self.validation_scores = validation_scores
        if self.training_scores is None:
            n_scores = EBMUtils.get_count_scores_c(self.num_classification_states)
            self.training_scores = np.zeros(y_train.shape[0] * n_scores, dtype=np.float64, order='C')
        if self.validation_scores is None:
            n_scores = EBMUtils.get_count_scores_c(self.num_classification_states)
            self.validation_scores = np.zeros(y_val.shape[0] * n_scores, dtype=np.float64, order='C')

        self.random_state = random_state

        # Convert n-dim arrays ready for C.
        self.X_train_f = np.asfortranarray(self.X_train)
        self.X_val_f = np.asfortranarray(self.X_val)

        # Define extra properties
        self.model_pointer = None
        self.interaction_pointer = None

        # Allocate external resources
        if self.model_type == "classification":
            self._initialize_training_classification()
            self._initialize_interaction_classification()
        elif self.model_type == "regression":
            self._initialize_training_regression()
            self._initialize_interaction_regression()
        else:
            raise AttributeError("Unrecognized model_type")

        log.info("Allocation end")

    def _convert_feature_info_to_c(self, features, feature_combinations):
        # Create C form of features
        feature_ar = (this.native.EbmCoreFeature * len(features))()
        for idx, feature in enumerate(features):
            if feature["type"] == "categorical":
                feature_ar[idx].featureType = this.native.FeatureTypeNominal
            elif feature["type"] == "continuous":
                feature_ar[idx].featureType = this.native.FeatureTypeOrdinal
            else:
                raise AttributeError("Unrecognized feature[\"type\"]")
            feature_ar[idx].hasMissing = 1 * feature["has_missing"]
            feature_ar[idx].countBins = feature["n_bins"]

        feature_combination_indexes = []
        feature_combinations_ar = (
            this.native.EbmCoreFeatureCombination * len(feature_combinations)
        )()
        for idx, feature_combination in enumerate(feature_combinations):
            features_in_combination = feature_combination["attributes"]
            feature_combinations_ar[idx].countFeaturesInCombination = len(features_in_combination)

            for feature_idx in features_in_combination:
                feature_combination_indexes.append(feature_idx)

        feature_combination_indexes = np.array(feature_combination_indexes, dtype=ct.c_longlong)

        return feature_ar, feature_combinations_ar, feature_combination_indexes

    def _initialize_training_classification(self):
        self.model_pointer = this.native.lib.InitializeTrainingClassification(
            self.random_state,
            len(self.feature_array),
            self.feature_array,
            len(self.feature_combinations_array),
            self.feature_combinations_array,
            self.feature_combination_indexes,
            self.num_classification_states,
            len(self.y_train),
            self.y_train,
            self.X_train_f,
            self.training_scores,
            len(self.y_val),
            self.y_val,
            self.X_val_f,
            self.validation_scores,
            self.num_inner_bags,
        )
        if not self.model_pointer:  # pragma: no cover
            raise MemoryError("Out of memory in InitializeTrainingClassification")

    def _initialize_training_regression(self):
        self.model_pointer = this.native.lib.InitializeTrainingRegression(
            self.random_state,
            len(self.feature_array),
            self.feature_array,
            len(self.feature_combinations_array),
            self.feature_combinations_array,
            self.feature_combination_indexes,
            len(self.y_train),
            self.y_train,
            self.X_train_f,
            self.training_scores,
            len(self.y_val),
            self.y_val,
            self.X_val_f,
            self.validation_scores,
            self.num_inner_bags,
        )
        if not self.model_pointer:  # pragma: no cover
            raise MemoryError("Out of memory in InitializeTrainingRegression")

    def _initialize_interaction_classification(self):
        self.interaction_pointer = this.native.lib.InitializeInteractionClassification(
            len(self.feature_array),
            self.feature_array,
            self.num_classification_states,
            len(self.y_train),
            self.y_train,
            self.X_train_f,
            self.training_scores,
        )
        if not self.interaction_pointer:  # pragma: no cover
            raise MemoryError("Out of memory in InitializeInteractionClassification")

    def _initialize_interaction_regression(self):
        self.interaction_pointer = this.native.lib.InitializeInteractionRegression(
            len(self.feature_array),
            self.feature_array,
            len(self.y_train),
            self.y_train,
            self.X_train_f,
            self.training_scores,
        )
        if not self.interaction_pointer:  # pragma: no cover
            raise MemoryError("Out of memory in InitializeInteractionRegression")

    def close(self):
        """ Deallocates C objects used to train EBM. """
        log.info("Deallocation start")
        this.native.lib.FreeTraining(self.model_pointer)
        this.native.lib.FreeInteraction(self.interaction_pointer)
        log.info("Deallocation end")

    def fast_interaction_score(self, feature_index_tuple):
        """ Provides score for an feature interaction. Higher is better."""
        log.info("Fast interaction score start")
        score = ct.c_double(0.0)
        return_code = this.native.lib.GetInteractionScore(
            self.interaction_pointer,
            len(feature_index_tuple),
            np.array(feature_index_tuple, dtype=np.int64),
            ct.byref(score),
        )
        if return_code != 0:  # pragma: no cover
            raise Exception("Out of memory in GetInteractionScore")

        log.info("Fast interaction score end")
        return score.value

    def training_step(
        self,
        feature_combination_index,
        training_step_episodes=1,
        learning_rate=0.01,
        max_tree_splits=2,
        min_cases_for_split=2,
        training_weights=0,
        validation_weights=0,
    ):

        """ Conducts a training step per feature
            by growing a shallow decision tree.

        Args:
            feature_combination_index: The index for the feature combination
                to train on.
            training_step_episodes: Number of episodes to train feature step.
            learning_rate: Learning rate as a float.
            max_tree_splits: Max tree splits on feature step.
            min_cases_for_split: Min observations required to split.
            training_weights: Training weights as float vector.
            validation_weights: Validation weights as float vector.

        Returns:
            Validation loss for the training step.
        """
        # log.debug("Training step start")

        metric_output = ct.c_double(0.0)
        # for a classification problem with only 1 target value, we will always predict the answer perfectly
        if self.model_type != "classification" or 2 <= self.num_classification_states:
            gain = ct.c_double(0.0)
            for i in range(training_step_episodes):
                model_update_tensor_pointer = this.native.lib.GenerateModelFeatureCombinationUpdate(
                    self.model_pointer,
                    feature_combination_index,
                    learning_rate,
                    max_tree_splits,
                    min_cases_for_split,
                    training_weights,
                    validation_weights,
                    ct.byref(gain),
                )
                if not model_update_tensor_pointer:  # pragma: no cover
                    raise MemoryError("Out of memory in GenerateModelFeatureCombinationUpdate")

                return_code = this.native.lib.ApplyModelFeatureCombinationUpdate(
                    self.model_pointer,
                    feature_combination_index,
                    model_update_tensor_pointer,
                    ct.byref(metric_output),
                )
                if return_code != 0:  # pragma: no cover
                    raise Exception("Out of memory in ApplyModelFeatureCombinationUpdate")

        # log.debug("Training step end")
        return metric_output.value

    def _get_feature_combination_shape(self, feature_combination_index):
        # Retrieve dimensions of log odds tensor
        dimensions = []
        feature_combination = self.feature_combinations[feature_combination_index]
        for _, feature_idx in enumerate(feature_combination["attributes"]):
            n_bins = self.features[feature_idx]["n_bins"]
            dimensions.append(n_bins)

        dimensions = list(reversed(dimensions))

        # Array returned for multiclass is one higher dimension
        if self.model_type == "classification" and self.num_classification_states > 2:
            dimensions.append(self.num_classification_states)

        shape = tuple(dimensions)
        return shape

    def get_best_model(self, feature_combination_index):
        """ Returns best model/function according to validation set
            for a given feature combination.

        Args:
            feature_combination_index: The index for the feature combination.

        Returns:
            An ndarray that represents the model.
        """

        # for a classification problem with only 1 target value, we will always predict the answer perfectly
        if self.model_type == "classification" and self.num_classification_states <= 1:
            return np.ndarray((0), np.double, order="C")

        array_p = this.native.lib.GetBestModelFeatureCombination(
            self.model_pointer, feature_combination_index
        )

        if not array_p:  # pragma: no cover
            raise MemoryError("Out of memory in GetBestModelFeatureCombination")

        shape = self._get_feature_combination_shape(feature_combination_index)

        array = make_ndarray(array_p, shape, dtype=np.double)
        return array

    def get_current_model(self, feature_combination_index):
        """ Returns current model/function according to validation set
            for a given feature combination.

        Args:
            feature_combination_index: The index for the feature combination.

        Returns:
            An ndarray that represents the model.
        """

        # for a classification problem with only 1 target value, we will always predict the answer perfectly
        if self.model_type == "classification" and self.num_classification_states <= 1:
            return np.ndarray((0), np.double, order="C")

        array_p = this.native.lib.GetCurrentModelFeatureCombination(
            self.model_pointer, feature_combination_index
        )

        if not array_p:  # pragma: no cover
            raise MemoryError("Out of memory in GetCurrentModelFeatureCombination")

        shape = self._get_feature_combination_shape(feature_combination_index)

        array = make_ndarray(array_p, shape, dtype=np.double)

        # if self.model_type == "classification" and self.num_classification_states > 2:
        #     array = array.T.reshape(array.shape)
        return array


def make_ndarray(c_pointer, shape, dtype, writable=False, copy_data=True):
    """ Returns an ndarray based from a C array.

    Code largely borrowed from:
    https://stackoverflow.com/questions/4355524/getting-data-from-ctypes-array-into-numpy

    Args:
        c_pointer: Pointer to C array.
        shape: Shape of ndarray to form.
        dtype: Numpy data type.

    Returns:
        An ndarray.
    """

    arr_size = np.prod(shape[:]) * np.dtype(dtype).itemsize
    buf_from_mem = ct.pythonapi.PyMemoryView_FromMemory
    buf_from_mem.restype = ct.py_object
    buf_from_mem.argtypes = (ct.c_void_p, ct.c_ssize_t, ct.c_int)
    PyBUF_READ = 0x100
    PyBUF_WRITE = 0x200
    access = (PyBUF_READ | PyBUF_WRITE) if writable else PyBUF_READ
    buffer = buf_from_mem(c_pointer, arr_size, access)
    # from https://github.com/python/cpython/blob/master/Objects/memoryobject.c , PyMemoryView_FromMemory can return null
    if not buffer:
        raise MemoryError("Out of memory in PyMemoryView_FromMemory")
    arr = np.ndarray(tuple(shape[:]), dtype, buffer, order="C")
    if copy_data:
        return arr.copy()
    else:
        return arr