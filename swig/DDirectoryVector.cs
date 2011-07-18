/* ----------------------------------------------------------------------------
 * This file was automatically generated by SWIG (http://www.swig.org).
 * Version 2.0.1
 *
 * Do not make changes to this file unless you know what you are doing--modify
 * the SWIG interface file instead.
 * ----------------------------------------------------------------------------- */

namespace ccdb {

using System;
using System.Runtime.InteropServices;

public class DDirectoryVector : IDisposable {
  private HandleRef swigCPtr;
  protected bool swigCMemOwn;

  internal DDirectoryVector(IntPtr cPtr, bool cMemoryOwn) {
    swigCMemOwn = cMemoryOwn;
    swigCPtr = new HandleRef(this, cPtr);
  }

  internal static HandleRef getCPtr(DDirectoryVector obj) {
    return (obj == null) ? new HandleRef(null, IntPtr.Zero) : obj.swigCPtr;
  }

  ~DDirectoryVector() {
    Dispose();
  }

  public virtual void Dispose() {
    lock(this) {
      if (swigCPtr.Handle != IntPtr.Zero) {
        if (swigCMemOwn) {
          swigCMemOwn = false;
          ccdb_csllapiPINVOKE.delete_DDirectoryVector(swigCPtr);
        }
        swigCPtr = new HandleRef(null, IntPtr.Zero);
      }
      GC.SuppressFinalize(this);
    }
  }

  public void Clear() {
    ccdb_csllapiPINVOKE.DDirectoryVector_Clear(swigCPtr);
  }

  public void Add(DDirectory x) {
    ccdb_csllapiPINVOKE.DDirectoryVector_Add(swigCPtr, DDirectory.getCPtr(x));
  }

  private uint size() {
    uint ret = ccdb_csllapiPINVOKE.DDirectoryVector_size(swigCPtr);
    return ret;
  }

  private uint capacity() {
    uint ret = ccdb_csllapiPINVOKE.DDirectoryVector_capacity(swigCPtr);
    return ret;
  }

  private void reserve(uint n) {
    ccdb_csllapiPINVOKE.DDirectoryVector_reserve(swigCPtr, n);
  }

  public DDirectoryVector() : this(ccdb_csllapiPINVOKE.new_DDirectoryVector__SWIG_0(), true) {
  }

  public DDirectoryVector(DDirectoryVector other) : this(ccdb_csllapiPINVOKE.new_DDirectoryVector__SWIG_1(DDirectoryVector.getCPtr(other)), true) {
    if (ccdb_csllapiPINVOKE.SWIGPendingException.Pending) throw ccdb_csllapiPINVOKE.SWIGPendingException.Retrieve();
  }

  public DDirectoryVector(int capacity) : this(ccdb_csllapiPINVOKE.new_DDirectoryVector__SWIG_2(capacity), true) {
    if (ccdb_csllapiPINVOKE.SWIGPendingException.Pending) throw ccdb_csllapiPINVOKE.SWIGPendingException.Retrieve();
  }

  private DDirectory getitemcopy(int index) {
    IntPtr cPtr = ccdb_csllapiPINVOKE.DDirectoryVector_getitemcopy(swigCPtr, index);
    DDirectory ret = (cPtr == IntPtr.Zero) ? null : new DDirectory(cPtr, false);
    if (ccdb_csllapiPINVOKE.SWIGPendingException.Pending) throw ccdb_csllapiPINVOKE.SWIGPendingException.Retrieve();
    return ret;
  }

  private DDirectory getitem(int index) {
    IntPtr cPtr = ccdb_csllapiPINVOKE.DDirectoryVector_getitem(swigCPtr, index);
    DDirectory ret = (cPtr == IntPtr.Zero) ? null : new DDirectory(cPtr, false);
    if (ccdb_csllapiPINVOKE.SWIGPendingException.Pending) throw ccdb_csllapiPINVOKE.SWIGPendingException.Retrieve();
    return ret;
  }

  private void setitem(int index, DDirectory val) {
    ccdb_csllapiPINVOKE.DDirectoryVector_setitem(swigCPtr, index, DDirectory.getCPtr(val));
    if (ccdb_csllapiPINVOKE.SWIGPendingException.Pending) throw ccdb_csllapiPINVOKE.SWIGPendingException.Retrieve();
  }

  public void AddRange(DDirectoryVector values) {
    ccdb_csllapiPINVOKE.DDirectoryVector_AddRange(swigCPtr, DDirectoryVector.getCPtr(values));
    if (ccdb_csllapiPINVOKE.SWIGPendingException.Pending) throw ccdb_csllapiPINVOKE.SWIGPendingException.Retrieve();
  }

  public DDirectoryVector GetRange(int index, int count) {
    IntPtr cPtr = ccdb_csllapiPINVOKE.DDirectoryVector_GetRange(swigCPtr, index, count);
    DDirectoryVector ret = (cPtr == IntPtr.Zero) ? null : new DDirectoryVector(cPtr, true);
    if (ccdb_csllapiPINVOKE.SWIGPendingException.Pending) throw ccdb_csllapiPINVOKE.SWIGPendingException.Retrieve();
    return ret;
  }

  public void Insert(int index, DDirectory x) {
    ccdb_csllapiPINVOKE.DDirectoryVector_Insert(swigCPtr, index, DDirectory.getCPtr(x));
    if (ccdb_csllapiPINVOKE.SWIGPendingException.Pending) throw ccdb_csllapiPINVOKE.SWIGPendingException.Retrieve();
  }

  public void InsertRange(int index, DDirectoryVector values) {
    ccdb_csllapiPINVOKE.DDirectoryVector_InsertRange(swigCPtr, index, DDirectoryVector.getCPtr(values));
    if (ccdb_csllapiPINVOKE.SWIGPendingException.Pending) throw ccdb_csllapiPINVOKE.SWIGPendingException.Retrieve();
  }

  public void RemoveAt(int index) {
    ccdb_csllapiPINVOKE.DDirectoryVector_RemoveAt(swigCPtr, index);
    if (ccdb_csllapiPINVOKE.SWIGPendingException.Pending) throw ccdb_csllapiPINVOKE.SWIGPendingException.Retrieve();
  }

  public void RemoveRange(int index, int count) {
    ccdb_csllapiPINVOKE.DDirectoryVector_RemoveRange(swigCPtr, index, count);
    if (ccdb_csllapiPINVOKE.SWIGPendingException.Pending) throw ccdb_csllapiPINVOKE.SWIGPendingException.Retrieve();
  }

  public static DDirectoryVector Repeat(DDirectory value, int count) {
    IntPtr cPtr = ccdb_csllapiPINVOKE.DDirectoryVector_Repeat(DDirectory.getCPtr(value), count);
    DDirectoryVector ret = (cPtr == IntPtr.Zero) ? null : new DDirectoryVector(cPtr, true);
    if (ccdb_csllapiPINVOKE.SWIGPendingException.Pending) throw ccdb_csllapiPINVOKE.SWIGPendingException.Retrieve();
    return ret;
  }

  public void Reverse() {
    ccdb_csllapiPINVOKE.DDirectoryVector_Reverse__SWIG_0(swigCPtr);
  }

  public void Reverse(int index, int count) {
    ccdb_csllapiPINVOKE.DDirectoryVector_Reverse__SWIG_1(swigCPtr, index, count);
    if (ccdb_csllapiPINVOKE.SWIGPendingException.Pending) throw ccdb_csllapiPINVOKE.SWIGPendingException.Retrieve();
  }

  public void SetRange(int index, DDirectoryVector values) {
    ccdb_csllapiPINVOKE.DDirectoryVector_SetRange(swigCPtr, index, DDirectoryVector.getCPtr(values));
    if (ccdb_csllapiPINVOKE.SWIGPendingException.Pending) throw ccdb_csllapiPINVOKE.SWIGPendingException.Retrieve();
  }

  public bool Contains(DDirectory value) {
    bool ret = ccdb_csllapiPINVOKE.DDirectoryVector_Contains(swigCPtr, DDirectory.getCPtr(value));
    return ret;
  }

  public int IndexOf(DDirectory value) {
    int ret = ccdb_csllapiPINVOKE.DDirectoryVector_IndexOf(swigCPtr, DDirectory.getCPtr(value));
    return ret;
  }

  public int LastIndexOf(DDirectory value) {
    int ret = ccdb_csllapiPINVOKE.DDirectoryVector_LastIndexOf(swigCPtr, DDirectory.getCPtr(value));
    return ret;
  }

  public bool Remove(DDirectory value) {
    bool ret = ccdb_csllapiPINVOKE.DDirectoryVector_Remove(swigCPtr, DDirectory.getCPtr(value));
    return ret;
  }

}

}
