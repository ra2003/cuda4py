"""
Copyright (c) 2014, Samsung Electronics Co.,Ltd.
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this
list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright notice,
this list of conditions and the following disclaimer in the documentation
and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

The views and conclusions contained in the software and documentation are those
of the authors and should not be interpreted as representing official policies,
either expressed or implied, of Samsung Electronics Co.,Ltd..
"""

"""
cuda4py - CUDA cffi bindings and helper classes.
URL: https://github.com/ajkxyz/cuda4py
Original author: Alexey Kazantsev <a.kazantsev@samsung.com>
"""

"""
cuRAND cffi bindings and helper classes.
"""
import cffi
import cuda4py._cffi as cuffi
from cuda4py._py import CU


#: ffi parser
ffi = None


#: Loaded shared library
lib = None


#: Error codes
CURAND_STATUS_SUCCESS = 0
CURAND_STATUS_VERSION_MISMATCH = 100
CURAND_STATUS_NOT_INITIALIZED = 101
CURAND_STATUS_ALLOCATION_FAILED = 102
CURAND_STATUS_TYPE_ERROR = 103
CURAND_STATUS_OUT_OF_RANGE = 104
CURAND_STATUS_LENGTH_NOT_MULTIPLE = 105
CURAND_STATUS_DOUBLE_PRECISION_REQUIRED = 106
CURAND_STATUS_LAUNCH_FAILURE = 201
CURAND_STATUS_PREEXISTING_FAILURE = 202
CURAND_STATUS_INITIALIZATION_FAILED = 203
CURAND_STATUS_ARCH_MISMATCH = 204
CURAND_STATUS_INTERNAL_ERROR = 999


#: Error descriptions
ERRORS = {
    CURAND_STATUS_VERSION_MISMATCH: "CURAND_STATUS_VERSION_MISMATCH",
    CURAND_STATUS_NOT_INITIALIZED: "CURAND_STATUS_NOT_INITIALIZED",
    CURAND_STATUS_ALLOCATION_FAILED: "CURAND_STATUS_ALLOCATION_FAILED",
    CURAND_STATUS_TYPE_ERROR: "CURAND_STATUS_TYPE_ERROR",
    CURAND_STATUS_OUT_OF_RANGE: "CURAND_STATUS_OUT_OF_RANGE",
    CURAND_STATUS_LENGTH_NOT_MULTIPLE: "CURAND_STATUS_LENGTH_NOT_MULTIPLE",
    CURAND_STATUS_DOUBLE_PRECISION_REQUIRED:
    "CURAND_STATUS_DOUBLE_PRECISION_REQUIRED",
    CURAND_STATUS_LAUNCH_FAILURE: "CURAND_STATUS_LAUNCH_FAILURE",
    CURAND_STATUS_PREEXISTING_FAILURE: "CURAND_STATUS_PREEXISTING_FAILURE",
    CURAND_STATUS_INITIALIZATION_FAILED: "CURAND_STATUS_INITIALIZATION_FAILED",
    CURAND_STATUS_ARCH_MISMATCH: "CURAND_STATUS_ARCH_MISMATCH",
    CURAND_STATUS_INTERNAL_ERROR: "CURAND_STATUS_INTERNAL_ERROR"
}


#: curandRngType
CURAND_RNG_TEST = 0
CURAND_RNG_PSEUDO_DEFAULT = 100  # Default pseudorandom
CURAND_RNG_PSEUDO_XORWOW = 101  # XORWOW pseudorandom
CURAND_RNG_PSEUDO_MRG32K3A = 121  # MRG32k3a pseudorandom
CURAND_RNG_PSEUDO_MTGP32 = 141  # Mersenne Twister MTGP32 pseudorandom
CURAND_RNG_PSEUDO_MT19937 = 142  # Mersenne Twister MT19937 pseudorandom
CURAND_RNG_PSEUDO_PHILOX4_32_10 = 161  # PHILOX-4x32-10 pseudorandom
CURAND_RNG_QUASI_DEFAULT = 200  # Default quasirandom
CURAND_RNG_QUASI_SOBOL32 = 201  # Sobol32 quasirandom
CURAND_RNG_QUASI_SCRAMBLED_SOBOL32 = 202  # Scrambled Sobol32 quasirandom
CURAND_RNG_QUASI_SOBOL64 = 203  # Sobol64 quasirandom
CURAND_RNG_QUASI_SCRAMBLED_SOBOL64 = 204  # Scrambled Sobol64 quasirandom


def _initialize(backends):
    global lib
    if lib is not None:
        return
    # C function definitions
    # size_t instead of void* is used
    # for convinience with python calls and numpy arrays,
    # cffi automatically calls int() on objects also.
    src = """
    typedef int curandStatus_t;
    typedef size_t curandGenerator_t;
    typedef int curandRngType_t;

    curandStatus_t curandCreateGenerator(
        curandGenerator_t *generator, curandRngType_t rng_type);
    curandStatus_t curandDestroyGenerator(curandGenerator_t generator);
    """

    # Parse
    global ffi
    ffi = cffi.FFI()
    ffi.cdef(src)

    # Load library
    for libnme in backends:
        try:
            lib = ffi.dlopen(libnme)
            break
        except OSError:
            pass
    else:
        ffi = None
        raise OSError("Could not load curand library")

    global ERRORS
    for code, msg in ERRORS.items():
        if code in CU.ERRORS:
            s = " | " + msg
            if s not in CU.ERRORS[code]:
                CU.ERRORS[code] += s
        else:
            CU.ERRORS[code] = msg


def initialize(backends=("libcurand.so", "curand64_65.dll")):
    """Loads shared library.
    """
    cuffi.initialize()
    global lib
    if lib is not None:
        return
    with cuffi.lock:
        _initialize(backends)


class CURAND(object):
    """cuRAND base object.
    """
    def __init__(self, context, rng_type=CURAND_RNG_PSEUDO_DEFAULT):
        self._context = context
        self._lib = None
        context._add_ref(self)
        initialize()
        handle = ffi.new("curandGenerator_t *")
        with context:
            err = lib.curandCreateGenerator(handle, rng_type)
        if err:
            self._handle = None
            raise CU.error("curandCreateGenerator", err)
        self._lib = lib  # to hold the reference
        self._handle = int(handle[0])

    def __int__(self):
        return self.handle

    @property
    def handle(self):
        return self._handle

    @property
    def context(self):
        return self._context

    def _release(self):
        if self._lib is not None and self.handle is not None:
            self._lib.curandDestroyGenerator(self.handle)
            self._handle = None

    def __del__(self):
        if self.context.handle is None:
            raise SystemError("Incorrect destructor call order detected")
        self._release()
        self.context._del_ref(self)
