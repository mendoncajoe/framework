// -*- mode: c++; -*-
// (Not really c++, but closest emacs mode)

%include "common.i"

%{
#include "level_1b.h"
%}

%base_import(generic_object)
%import "double_with_unit.i"
%import "array_with_unit.i"
%import "fp_time.i"
%import "spectral_range.i"
%import "spectral_domain.i"
%fp_shared_ptr(FullPhysics::Level1b);

namespace FullPhysics {
class Level1b : public GenericObject {
public:
  virtual ~Level1b();
  std::string print_to_string() const;
  %python_attribute(number_spectrometer, virtual int);
  virtual DoubleWithUnit latitude(int i) const = 0;
  virtual DoubleWithUnit longitude(int i) const = 0;
  virtual DoubleWithUnit sounding_zenith(int i) const = 0;
  virtual DoubleWithUnit sounding_azimuth(int i) const = 0;
  virtual blitz::Array<double, 1> stokes_coefficient(int i) const = 0;
  virtual DoubleWithUnit solar_zenith(int i) const = 0;
  virtual DoubleWithUnit solar_azimuth(int i) const = 0;
  virtual DoubleWithUnit relative_azimuth(int i) const = 0;
  virtual DoubleWithUnit altitude(int i) const = 0;
  virtual DoubleWithUnit relative_velocity(int i) const = 0;
  virtual SpectralDomain sample_grid(int Spec_index) const = 0;  
  virtual Time time(int Spec_index) const = 0;
  virtual SpectralRange radiance(int Spec_index) const = 0;
  virtual DoubleWithUnit signal(int Spec_index, const std::vector<int>& Sample_indexes = std::vector<int>()) const;
};
}
