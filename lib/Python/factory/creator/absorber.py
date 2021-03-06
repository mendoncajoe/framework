import os
from glob import glob
from enum import Enum

import numpy as np

from .base import Creator, ParamPassThru
from .value import CreatorFlaggedValue
from .util import ExtendedFormatter
from .. import param

from refractor import framework as rf

DEFAULT_REFERENCE_ATM_FILENAME = os.path.join(os.environ.get("REFRACTOR_INPUTS", "$ENV{REFRACTOR_INPUTS}"), "reference_atmosphere.h5")

class ReferenceAtmFileMixin(object):

    def ref_atm_data(self):

        if self.reference_atm_file() is not None:
            if not os.path.exists(self.reference_atm_file()):
                raise param.ParamError("Could not find reference atmosphere file supplied through config: %s" % self.reference_atm_file())

            ref_atm_data = rf.HdfFile(self.reference_atm_file())
        else:
            if not os.path.exists(DEFAULT_REFERENCE_ATM_FILENAME):
                raise param.ParamError("Could not find default reference atmosphere file: %s" % DEFAULT_REFERENCE_ATM_FILENAME)

            ref_atm_data = rf.HdfFile(DEFAULT_REFERENCE_ATM_FILENAME)

        return ref_atm_data

class GasVmrAprioriMetL1b(Creator, ReferenceAtmFileMixin):
    "Creates a VMR apriori for a gas species using the TCCON method"

    l1b = param.InstanceOf(rf.Level1b)
    met = param.InstanceOf(rf.Meteorology)
    pressure = param.InstanceOf(rf.Pressure)
    altitude = param.ObjectVector("altitude")
    temp_avg_window = param.Scalar(int, default=11)

    # Normally passed from through the create method from the AbsorberGasDefinition creator
    gas_name = param.Scalar(str, required=False)

    # Normally use the distributed version of this file
    reference_atm_file = param.Scalar(str, required=False)

    def create(self, gas_name=None, **kwargs):

        if self.gas_name() is not None:
            gas_name = self.gas_name()
        elif gas_name is None:
            raise param.ParamError("gas_name not supplied to creator %s" % self.__class__.__name__)

        apriori_obj = rf.GasVmrApriori(self.met(), self.l1b(), self.altitude()[0], self.ref_atm_data(), "/Reference_Atmosphere", gas_name, self.temp_avg_window())
        return apriori_obj.apriori_vmr(self.pressure())

class GasVmrApriori(Creator, ReferenceAtmFileMixin):
    "Creates a VMR apriori for a gas species using the TCCON method"

    pressure = param.InstanceOf(rf.Pressure)
    temperature = param.InstanceOf(rf.Temperature)
    latitude = param.ArrayWithUnit(dims=1)
    time = param.Iterable(rf.Time)
    altitude = param.ObjectVector("altitude")
    reference_atm_file = param.Scalar(str)
    temp_avg_window = param.Scalar(int, default=11)

    # Normally passed from through the create method from the AbsorberGasDefinition creator
    gas_name = param.Scalar(str, required=False)

    # Normally use the distributed version of this file
    reference_atm_file = param.Scalar(str, required=False)

    def create(self, gas_name=None, **kwargs):

        if self.gas_name() is not None:
            gas_name = self.gas_name()
        elif gas_name is None:
            raise param.ParamError("gas_name not supplied to creator %s" % self.__class__.__name__)

        pressure_levels = self.pressure().pressure_grid.value.value
        temperature_levels = self.temperature().temperature_grid(self.pressure()).value.value

        apriori_obj = rf.GasVmrApriori(pressure_levels, temperature_levels, self.latitude().value[0], self.time()[0], \
                self.altitude()[0], self.ref_atm_data(), "/Reference_Atmosphere", gas_name, self.temp_avg_window())
        vmr_profile = apriori_obj.apriori_vmr()

        if np.any(np.isnan(vmr_profile)):
            raise param.ParamError("NaN values detected in VMR computed by GasVmrApriori for {}".format(gas_name))

        return vmr_profile

class AbsorberVmrLevel(CreatorFlaggedValue):
    "Creates a AbsorberVmrLevel that supplies a AbsorberVmr class for use in an creating an Atmosphere"

    pressure = param.InstanceOf(rf.Pressure)
    log_retrieval = param.Scalar(bool, default=False)

    # Normally passed from through the create method from the AbsorberGasDefinition creator
    gas_name = param.Scalar(str, required=False)

    def create(self, gas_name=None, **kwargs):

        if self.gas_name() is not None:
            gas_name = self.gas_name()
        elif gas_name is None:
            raise param.ParamError("gas_name not supplied to creator %s" % self.__class__.__name__)

        vmr_profile = self.value(gas_name=gas_name)

        if np.any(np.isnan(vmr_profile)):
            raise param.ParamError("NaN values detected in VMR profile supplied for {}".format(gas_name))

        if self.log_retrieval and np.any(vmr_profile < 0):
            raise param.ParamError("Log retrieval selected and negative values in VMR profile for {}".format(gas_name))

        if self.log_retrieval:
            return rf.AbsorberVmrLevelLog(self.pressure(), vmr_profile, self.retrieval_flag(gas_name=gas_name), gas_name)
        else:
            return rf.AbsorberVmrLevel(self.pressure(), vmr_profile, self.retrieval_flag(gas_name=gas_name), gas_name)

class AbsorberVmrLevelScaled(CreatorFlaggedValue):
    "Creates a AbsorberVmrLevelScaled that supplies a AbsorberVmr class for use in an creating an Atmosphere"

    pressure = param.InstanceOf(rf.Pressure)

    # Normally passed from through the create method from the AbsorberGasDefinition creator
    gas_name = param.Scalar(str, required=False)
    scaling = param.Scalar(float, required=False, default=1.0)

    def create(self, gas_name=None, **kwargs):

        if self.gas_name() is not None:
            gas_name = self.gas_name()
        elif gas_name is None:
            raise param.ParamError("gas_name not supplied to creator %s" % self.__class__.__name__)

        vmr_profile = self.value(gas_name=gas_name)

        if np.any(np.isnan(vmr_profile)):
            raise param.ParamError("NaN values detected in VMR profile supplied for {}".format(gas_name))

        ret_flag = bool(self.retrieval_flag(gas_name=gas_name)[0])
        return rf.AbsorberVmrLevelScaled(self.pressure(), vmr_profile, self.scaling(), ret_flag, gas_name)

class AbsorberVmrMet(CreatorFlaggedValue):

    met = param.InstanceOf(rf.Meteorology)
    pressure = param.InstanceOf(rf.Pressure)

    def create(self, gas_name=None, **kwargs):

        if gas_name is None:
            raise param.ParamError("gas_name not supplied to creator %s" % self.__class__.__name__)

        return rf.AbsorberVmrMet(self.met(), self.pressure(), self.value(gas_name=gas_name)[0], bool(self.retrieval_flag(gas_name=gas_name)[0]), gas_name)

class AbscoCreator(Creator):
    "Do not use directly, defines the generic interface that uses a specific Absco class specified in inheriting creators"

    absco_base_path = param.Scalar(str)
    filename = param.Scalar(str)
    table_scale = param.Choice(param.Iterable(), param.Scalar(float), default=1.0)
    spec_win = param.InstanceOf(rf.SpectralWindow)

    def absco_object(self, absco_filename, table_scale, spectral_bound=None):
        raise NotImplementedError("Do not use AbscoCreator directly, instead use an inherited creator that defines the type of ABSCO file reader to use")

    def create(self, gas_name=None, **kwargs):

        # Use ExtendedFormatter that allows using l and u conversion codes for upper/lower case conversion
        fn_formatter = ExtendedFormatter()
        try:
            absco_filename = fn_formatter.format(self.filename(), gas=gas_name, **self.common_store)
        except ValueError as exc:
            raise param.ParamError('Error formatting absco filename template "%s": %s' % (self.filename(), exc))
        
        # Try expanding globs
        if not os.path.exists(absco_filename):
            filename_matches = glob(absco_filename)

            if len(filename_matches) > 1:
                raise param.ParamError("ABSCO filename expanded to multiple files: %s" % absco_filename)
            else:
                absco_filename = filename_matches[0]

        # Error if filename still not found
        if not os.path.exists(absco_filename):
            raise param.ParamError("HDF ABSCO filename does not exist: %s" % absco_filename)

        table_scale = self.table_scale()

        if np.isscalar(table_scale):
            return self.absco_object(absco_filename, table_scale)
        else:
            spectral_bound = self.spec_win().spectral_bound

            # Convert to vector to match interface
            table_scale_vector = rf.vector_double()
            for val in table_scale:
                table_scale_vector.push_back(val)

            return self.absco_object(absco_filename, table_scale_vector, spectral_bound)

class AbscoLegacy(AbscoCreator):
    "Legacy HDF format created for OCO"

    def absco_object(self, absco_filename, table_scale, spectral_bound=None):

        if spectral_bound is not None:
            return rf.AbscoHdf(absco_filename, spectral_bound, table_scale)
        else:
            return rf.AbscoHdf(absco_filename, table_scale)

class AbscoInterpolationOption(Enum):
    error = rf.AbscoAer.THROW_ERROR_IF_NOT_ON_WN_GRID
    nearest_neighbor = rf.AbscoAer.NEAREST_NEIGHBOR_WN
    interpolate = rf.AbscoAer.INTERPOLATE_WN

class AbscoAer(AbscoCreator):
    "Newer AER generated ABSCO format"

    interp_method = param.Choice(param.Scalar(int), param.InstanceOf(AbscoInterpolationOption), default=0)
    cache_size = param.Scalar(int, default=5000)

    def absco_object(self, absco_filename, table_scale, spectral_bound=None):

        interp_method = self.interp_method()
        cache_size = self.cache_size()

        # Convert to integer
        if isinstance(interp_method, AbscoInterpolationOption):
            interp_method = interp_method.value

        if spectral_bound is not None:
            return rf.AbscoAer(absco_filename, spectral_bound, table_scale, cache_size, interp_method)
        else:
            return rf.AbscoAer(absco_filename, table_scale, cache_size, interp_method)


class AbsorberGasDefinition(ParamPassThru):
    "Defines the interface expected for VMR config defnition blocks, values are pass through as a dictionary"

    vmr = param.InstanceOf(rf.AbsorberVmr)
    absorption = param.InstanceOf(rf.GasAbsorption)

class AbsorberAbsco(Creator):
    "Creates an AbsorberAbsco object that statisfies the AtmosphereCreato;rs absorber value"

    gases = param.Iterable()
    pressure = param.InstanceOf(rf.Pressure)
    temperature = param.InstanceOf(rf.Temperature)
    altitude = param.ObjectVector("altitude")
    num_sub_layers = param.Scalar(int, required=False)
    constants = param.InstanceOf(rf.Constant)
    default_gas_definition = param.Dict(required=False)
            
    def create(self, **kwargs):

        vmrs = rf.vector_absorber_vmr()
        absorptions = rf.vector_gas_absorption()

        for gas_name in self.gases():
            if gas_name in self.config_def:
                self.register_parameter(gas_name, param.Dict())
                gas_def = self.param(gas_name, gas_name=gas_name)
            else:
                gas_def = self.default_gas_definition(gas_name=gas_name)
            
            if gas_def is None:
                raise param.ParamError("No definition for gas %s and no default_gas_defintion block defined" % gas_name)

            if not "vmr" in gas_def:
                raise param.ParamError("vmr value not in gas definition for gas: %s" % gas_name)

            if not "absorption" in gas_def:
                raise param.ParamError("absorption value not in gas definition for gas: %s" % gas_name)

            vmrs.push_back(gas_def['vmr'])
            absorptions.push_back(gas_def['absorption'])

        if self.num_sub_layers() is not None:
            return rf.AbsorberAbsco(vmrs, self.pressure(), self.temperature(), self.altitude(), absorptions, self.constants(), self.number_sub_layers())
        else:
            return rf.AbsorberAbsco(vmrs, self.pressure(), self.temperature(), self.altitude(), absorptions, self.constants())

