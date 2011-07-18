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

class ccdb_csllapiPINVOKE {

  protected class SWIGExceptionHelper {

    public delegate void ExceptionDelegate(string message);
    public delegate void ExceptionArgumentDelegate(string message, string paramName);

    static ExceptionDelegate applicationDelegate = new ExceptionDelegate(SetPendingApplicationException);
    static ExceptionDelegate arithmeticDelegate = new ExceptionDelegate(SetPendingArithmeticException);
    static ExceptionDelegate divideByZeroDelegate = new ExceptionDelegate(SetPendingDivideByZeroException);
    static ExceptionDelegate indexOutOfRangeDelegate = new ExceptionDelegate(SetPendingIndexOutOfRangeException);
    static ExceptionDelegate invalidCastDelegate = new ExceptionDelegate(SetPendingInvalidCastException);
    static ExceptionDelegate invalidOperationDelegate = new ExceptionDelegate(SetPendingInvalidOperationException);
    static ExceptionDelegate ioDelegate = new ExceptionDelegate(SetPendingIOException);
    static ExceptionDelegate nullReferenceDelegate = new ExceptionDelegate(SetPendingNullReferenceException);
    static ExceptionDelegate outOfMemoryDelegate = new ExceptionDelegate(SetPendingOutOfMemoryException);
    static ExceptionDelegate overflowDelegate = new ExceptionDelegate(SetPendingOverflowException);
    static ExceptionDelegate systemDelegate = new ExceptionDelegate(SetPendingSystemException);

    static ExceptionArgumentDelegate argumentDelegate = new ExceptionArgumentDelegate(SetPendingArgumentException);
    static ExceptionArgumentDelegate argumentNullDelegate = new ExceptionArgumentDelegate(SetPendingArgumentNullException);
    static ExceptionArgumentDelegate argumentOutOfRangeDelegate = new ExceptionArgumentDelegate(SetPendingArgumentOutOfRangeException);

    [DllImport("ccdb_csllapi", EntryPoint="SWIGRegisterExceptionCallbacks_ccdb_csllapi")]
    public static extern void SWIGRegisterExceptionCallbacks_ccdb_csllapi(
                                ExceptionDelegate applicationDelegate,
                                ExceptionDelegate arithmeticDelegate,
                                ExceptionDelegate divideByZeroDelegate, 
                                ExceptionDelegate indexOutOfRangeDelegate, 
                                ExceptionDelegate invalidCastDelegate,
                                ExceptionDelegate invalidOperationDelegate,
                                ExceptionDelegate ioDelegate,
                                ExceptionDelegate nullReferenceDelegate,
                                ExceptionDelegate outOfMemoryDelegate, 
                                ExceptionDelegate overflowDelegate, 
                                ExceptionDelegate systemExceptionDelegate);

    [DllImport("ccdb_csllapi", EntryPoint="SWIGRegisterExceptionArgumentCallbacks_ccdb_csllapi")]
    public static extern void SWIGRegisterExceptionCallbacksArgument_ccdb_csllapi(
                                ExceptionArgumentDelegate argumentDelegate,
                                ExceptionArgumentDelegate argumentNullDelegate,
                                ExceptionArgumentDelegate argumentOutOfRangeDelegate);

    static void SetPendingApplicationException(string message) {
      SWIGPendingException.Set(new System.ApplicationException(message, SWIGPendingException.Retrieve()));
    }
    static void SetPendingArithmeticException(string message) {
      SWIGPendingException.Set(new System.ArithmeticException(message, SWIGPendingException.Retrieve()));
    }
    static void SetPendingDivideByZeroException(string message) {
      SWIGPendingException.Set(new System.DivideByZeroException(message, SWIGPendingException.Retrieve()));
    }
    static void SetPendingIndexOutOfRangeException(string message) {
      SWIGPendingException.Set(new System.IndexOutOfRangeException(message, SWIGPendingException.Retrieve()));
    }
    static void SetPendingInvalidCastException(string message) {
      SWIGPendingException.Set(new System.InvalidCastException(message, SWIGPendingException.Retrieve()));
    }
    static void SetPendingInvalidOperationException(string message) {
      SWIGPendingException.Set(new System.InvalidOperationException(message, SWIGPendingException.Retrieve()));
    }
    static void SetPendingIOException(string message) {
      SWIGPendingException.Set(new System.IO.IOException(message, SWIGPendingException.Retrieve()));
    }
    static void SetPendingNullReferenceException(string message) {
      SWIGPendingException.Set(new System.NullReferenceException(message, SWIGPendingException.Retrieve()));
    }
    static void SetPendingOutOfMemoryException(string message) {
      SWIGPendingException.Set(new System.OutOfMemoryException(message, SWIGPendingException.Retrieve()));
    }
    static void SetPendingOverflowException(string message) {
      SWIGPendingException.Set(new System.OverflowException(message, SWIGPendingException.Retrieve()));
    }
    static void SetPendingSystemException(string message) {
      SWIGPendingException.Set(new System.SystemException(message, SWIGPendingException.Retrieve()));
    }

    static void SetPendingArgumentException(string message, string paramName) {
      SWIGPendingException.Set(new System.ArgumentException(message, paramName, SWIGPendingException.Retrieve()));
    }
    static void SetPendingArgumentNullException(string message, string paramName) {
      Exception e = SWIGPendingException.Retrieve();
      if (e != null) message = message + " Inner Exception: " + e.Message;
      SWIGPendingException.Set(new System.ArgumentNullException(paramName, message));
    }
    static void SetPendingArgumentOutOfRangeException(string message, string paramName) {
      Exception e = SWIGPendingException.Retrieve();
      if (e != null) message = message + " Inner Exception: " + e.Message;
      SWIGPendingException.Set(new System.ArgumentOutOfRangeException(paramName, message));
    }

    static SWIGExceptionHelper() {
      SWIGRegisterExceptionCallbacks_ccdb_csllapi(
                                applicationDelegate,
                                arithmeticDelegate,
                                divideByZeroDelegate,
                                indexOutOfRangeDelegate,
                                invalidCastDelegate,
                                invalidOperationDelegate,
                                ioDelegate,
                                nullReferenceDelegate,
                                outOfMemoryDelegate,
                                overflowDelegate,
                                systemDelegate);

      SWIGRegisterExceptionCallbacksArgument_ccdb_csllapi(
                                argumentDelegate,
                                argumentNullDelegate,
                                argumentOutOfRangeDelegate);
    }
  }

  protected static SWIGExceptionHelper swigExceptionHelper = new SWIGExceptionHelper();

  public class SWIGPendingException {
    [ThreadStatic]
    private static Exception pendingException = null;
    private static int numExceptionsPending = 0;

    public static bool Pending {
      get {
        bool pending = false;
        if (numExceptionsPending > 0)
          if (pendingException != null)
            pending = true;
        return pending;
      } 
    }

    public static void Set(Exception e) {
      if (pendingException != null)
        throw new ApplicationException("FATAL: An earlier pending exception from unmanaged code was missed and thus not thrown (" + pendingException.ToString() + ")", e);
      pendingException = e;
      lock(typeof(ccdb_csllapiPINVOKE)) {
        numExceptionsPending++;
      }
    }

    public static Exception Retrieve() {
      Exception e = null;
      if (numExceptionsPending > 0) {
        if (pendingException != null) {
          e = pendingException;
          pendingException = null;
          lock(typeof(ccdb_csllapiPINVOKE)) {
            numExceptionsPending--;
          }
        }
      }
      return e;
    }
  }


  protected class SWIGStringHelper {

    public delegate string SWIGStringDelegate(string message);
    static SWIGStringDelegate stringDelegate = new SWIGStringDelegate(CreateString);

    [DllImport("ccdb_csllapi", EntryPoint="SWIGRegisterStringCallback_ccdb_csllapi")]
    public static extern void SWIGRegisterStringCallback_ccdb_csllapi(SWIGStringDelegate stringDelegate);

    static string CreateString(string cString) {
      return cString;
    }

    static SWIGStringHelper() {
      SWIGRegisterStringCallback_ccdb_csllapi(stringDelegate);
    }
  }

  static protected SWIGStringHelper swigStringHelper = new SWIGStringHelper();


  static ccdb_csllapiPINVOKE() {
  }


  [DllImport("ccdb_csllapi", EntryPoint="CSharp_new_DRunRange")]
  public static extern IntPtr new_DRunRange();

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_delete_DRunRange")]
  public static extern void delete_DRunRange(HandleRef jarg1);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_DRunRange_GetId")]
  public static extern int DRunRange_GetId(HandleRef jarg1);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_DRunRange_GetMax")]
  public static extern int DRunRange_GetMax(HandleRef jarg1);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_DRunRange_GetMin")]
  public static extern int DRunRange_GetMin(HandleRef jarg1);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_DRunRange_GetName")]
  public static extern string DRunRange_GetName(HandleRef jarg1);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_DRunRange_GetComment")]
  public static extern string DRunRange_GetComment(HandleRef jarg1);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_DRunRange_SetId")]
  public static extern void DRunRange_SetId(HandleRef jarg1, int jarg2);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_DRunRange_SetMax")]
  public static extern void DRunRange_SetMax(HandleRef jarg1, int jarg2);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_DRunRange_SetMin")]
  public static extern void DRunRange_SetMin(HandleRef jarg1, int jarg2);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_DRunRange_SetName")]
  public static extern void DRunRange_SetName(HandleRef jarg1, string jarg2);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_DRunRange_SetComment")]
  public static extern void DRunRange_SetComment(HandleRef jarg1, string jarg2);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_DRunRange_SetRange")]
  public static extern void DRunRange_SetRange(HandleRef jarg1, int jarg2, int jarg3);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_DRunRange_GetCreatedTime")]
  public static extern IntPtr DRunRange_GetCreatedTime(HandleRef jarg1);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_DRunRange_SetCreatedTime")]
  public static extern void DRunRange_SetCreatedTime(HandleRef jarg1, HandleRef jarg2);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_DRunRange_GetModifiedTime")]
  public static extern IntPtr DRunRange_GetModifiedTime(HandleRef jarg1);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_DRunRange_SetModifiedTime")]
  public static extern void DRunRange_SetModifiedTime(HandleRef jarg1, HandleRef jarg2);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_new_DDirectory")]
  public static extern IntPtr new_DDirectory();

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_delete_DDirectory")]
  public static extern void delete_DDirectory(HandleRef jarg1);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_DDirectory_GetParentDirectory")]
  public static extern IntPtr DDirectory_GetParentDirectory(HandleRef jarg1);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_DDirectory_GetSubdirectories")]
  public static extern IntPtr DDirectory_GetSubdirectories(HandleRef jarg1);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_DDirectory_AddSubdirectory")]
  public static extern void DDirectory_AddSubdirectory(HandleRef jarg1, HandleRef jarg2);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_DDirectory_DisposeSubdirectories")]
  public static extern void DDirectory_DisposeSubdirectories(HandleRef jarg1);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_DDirectory_GetId")]
  public static extern uint DDirectory_GetId(HandleRef jarg1);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_DDirectory_SetId")]
  public static extern void DDirectory_SetId(HandleRef jarg1, uint jarg2);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_DDirectory_GetParentId")]
  public static extern uint DDirectory_GetParentId(HandleRef jarg1);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_DDirectory_SetParentId")]
  public static extern void DDirectory_SetParentId(HandleRef jarg1, uint jarg2);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_DDirectory_GetName")]
  public static extern string DDirectory_GetName(HandleRef jarg1);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_DDirectory_SetName")]
  public static extern void DDirectory_SetName(HandleRef jarg1, string jarg2);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_DDirectory_GetFullPath")]
  public static extern string DDirectory_GetFullPath(HandleRef jarg1);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_DDirectory_SetFullPath")]
  public static extern void DDirectory_SetFullPath(HandleRef jarg1, string jarg2);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_DDirectory_GetCreatedTime")]
  public static extern IntPtr DDirectory_GetCreatedTime(HandleRef jarg1);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_DDirectory_SetCreatedTime")]
  public static extern void DDirectory_SetCreatedTime(HandleRef jarg1, HandleRef jarg2);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_DDirectory_GetModifiedTime")]
  public static extern IntPtr DDirectory_GetModifiedTime(HandleRef jarg1);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_DDirectory_SetModifiedTime")]
  public static extern void DDirectory_SetModifiedTime(HandleRef jarg1, HandleRef jarg2);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_DDirectory_GetComment")]
  public static extern string DDirectory_GetComment(HandleRef jarg1);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_DDirectory_SetComment")]
  public static extern void DDirectory_SetComment(HandleRef jarg1, string jarg2);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_delete_DDataProvider")]
  public static extern void delete_DDataProvider(HandleRef jarg1);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_DDataProvider_Connect")]
  public static extern bool DDataProvider_Connect(HandleRef jarg1, string jarg2);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_DDataProvider_Disconnect")]
  public static extern void DDataProvider_Disconnect(HandleRef jarg1);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_DDataProvider_IsConnected")]
  public static extern bool DDataProvider_IsConnected(HandleRef jarg1);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_DDataProvider_GetDirectory")]
  public static extern IntPtr DDataProvider_GetDirectory(HandleRef jarg1, string jarg2);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_new_DMySQLDataProvider")]
  public static extern IntPtr new_DMySQLDataProvider();

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_delete_DMySQLDataProvider")]
  public static extern void delete_DMySQLDataProvider(HandleRef jarg1);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_DMySQLDataProvider_Connect")]
  public static extern bool DMySQLDataProvider_Connect(HandleRef jarg1, string jarg2);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_DMySQLDataProvider_IsConnected")]
  public static extern bool DMySQLDataProvider_IsConnected(HandleRef jarg1);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_DMySQLDataProvider_Disconnect")]
  public static extern void DMySQLDataProvider_Disconnect(HandleRef jarg1);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_DMySQLDataProvider_GetDirectory")]
  public static extern IntPtr DMySQLDataProvider_GetDirectory(HandleRef jarg1, string jarg2);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_new_DConstantsTypeTable")]
  public static extern IntPtr new_DConstantsTypeTable();

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_delete_DConstantsTypeTable")]
  public static extern void delete_DConstantsTypeTable(HandleRef jarg1);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_DConstantsTypeTable_SetDirectory")]
  public static extern void DConstantsTypeTable_SetDirectory(HandleRef jarg1, HandleRef jarg2);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_DConstantsTypeTable_GetDirectory")]
  public static extern IntPtr DConstantsTypeTable_GetDirectory(HandleRef jarg1);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_DConstantsTypeTable_SetDirectoryId")]
  public static extern void DConstantsTypeTable_SetDirectoryId(HandleRef jarg1, int jarg2);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_DConstantsTypeTable_GetDirectoryId")]
  public static extern int DConstantsTypeTable_GetDirectoryId(HandleRef jarg1);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_DConstantsTypeTable_SetFullPath")]
  public static extern void DConstantsTypeTable_SetFullPath(HandleRef jarg1, HandleRef jarg2);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_DConstantsTypeTable_GetFullPath")]
  public static extern IntPtr DConstantsTypeTable_GetFullPath(HandleRef jarg1);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_DConstantsTypeTable_SetId")]
  public static extern void DConstantsTypeTable_SetId(HandleRef jarg1, uint jarg2);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_DConstantsTypeTable_GetId")]
  public static extern int DConstantsTypeTable_GetId(HandleRef jarg1);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_DConstantsTypeTable_SetName")]
  public static extern void DConstantsTypeTable_SetName(HandleRef jarg1, HandleRef jarg2);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_DConstantsTypeTable_GetName")]
  public static extern IntPtr DConstantsTypeTable_GetName(HandleRef jarg1);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_DConstantsTypeTable_GetComment")]
  public static extern string DConstantsTypeTable_GetComment(HandleRef jarg1);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_DConstantsTypeTable_SetComment")]
  public static extern void DConstantsTypeTable_SetComment(HandleRef jarg1, HandleRef jarg2);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_DConstantsTypeTable_GetCreatedTime")]
  public static extern IntPtr DConstantsTypeTable_GetCreatedTime(HandleRef jarg1);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_DConstantsTypeTable_SetCreatedTime")]
  public static extern void DConstantsTypeTable_SetCreatedTime(HandleRef jarg1, HandleRef jarg2);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_DConstantsTypeTable_GetModifiedTime")]
  public static extern IntPtr DConstantsTypeTable_GetModifiedTime(HandleRef jarg1);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_DConstantsTypeTable_SetModifiedTime")]
  public static extern void DConstantsTypeTable_SetModifiedTime(HandleRef jarg1, HandleRef jarg2);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_DConstantsTypeTable_GetNRows")]
  public static extern int DConstantsTypeTable_GetNRows(HandleRef jarg1);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_DConstantsTypeTable_SetNRows")]
  public static extern void DConstantsTypeTable_SetNRows(HandleRef jarg1, int jarg2);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_DConstantsTypeTable_GetNColumns")]
  public static extern int DConstantsTypeTable_GetNColumns(HandleRef jarg1);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_DConstantsTypeTable_GetNColumnsFromDB")]
  public static extern int DConstantsTypeTable_GetNColumnsFromDB(HandleRef jarg1);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_DConstantsTypeTable_SetNColumnsFromDB")]
  public static extern void DConstantsTypeTable_SetNColumnsFromDB(HandleRef jarg1, int jarg2);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_DConstantsTypeTable_ClearColumns")]
  public static extern void DConstantsTypeTable_ClearColumns(HandleRef jarg1);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_DConstantsTypeTable_GetColumnNames")]
  public static extern IntPtr DConstantsTypeTable_GetColumnNames(HandleRef jarg1);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_DConstantsTypeTable_GetColumnTypeStrings")]
  public static extern IntPtr DConstantsTypeTable_GetColumnTypeStrings(HandleRef jarg1);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_DDirectoryVector_Clear")]
  public static extern void DDirectoryVector_Clear(HandleRef jarg1);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_DDirectoryVector_Add")]
  public static extern void DDirectoryVector_Add(HandleRef jarg1, HandleRef jarg2);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_DDirectoryVector_size")]
  public static extern uint DDirectoryVector_size(HandleRef jarg1);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_DDirectoryVector_capacity")]
  public static extern uint DDirectoryVector_capacity(HandleRef jarg1);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_DDirectoryVector_reserve")]
  public static extern void DDirectoryVector_reserve(HandleRef jarg1, uint jarg2);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_new_DDirectoryVector__SWIG_0")]
  public static extern IntPtr new_DDirectoryVector__SWIG_0();

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_new_DDirectoryVector__SWIG_1")]
  public static extern IntPtr new_DDirectoryVector__SWIG_1(HandleRef jarg1);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_new_DDirectoryVector__SWIG_2")]
  public static extern IntPtr new_DDirectoryVector__SWIG_2(int jarg1);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_DDirectoryVector_getitemcopy")]
  public static extern IntPtr DDirectoryVector_getitemcopy(HandleRef jarg1, int jarg2);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_DDirectoryVector_getitem")]
  public static extern IntPtr DDirectoryVector_getitem(HandleRef jarg1, int jarg2);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_DDirectoryVector_setitem")]
  public static extern void DDirectoryVector_setitem(HandleRef jarg1, int jarg2, HandleRef jarg3);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_DDirectoryVector_AddRange")]
  public static extern void DDirectoryVector_AddRange(HandleRef jarg1, HandleRef jarg2);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_DDirectoryVector_GetRange")]
  public static extern IntPtr DDirectoryVector_GetRange(HandleRef jarg1, int jarg2, int jarg3);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_DDirectoryVector_Insert")]
  public static extern void DDirectoryVector_Insert(HandleRef jarg1, int jarg2, HandleRef jarg3);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_DDirectoryVector_InsertRange")]
  public static extern void DDirectoryVector_InsertRange(HandleRef jarg1, int jarg2, HandleRef jarg3);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_DDirectoryVector_RemoveAt")]
  public static extern void DDirectoryVector_RemoveAt(HandleRef jarg1, int jarg2);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_DDirectoryVector_RemoveRange")]
  public static extern void DDirectoryVector_RemoveRange(HandleRef jarg1, int jarg2, int jarg3);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_DDirectoryVector_Repeat")]
  public static extern IntPtr DDirectoryVector_Repeat(HandleRef jarg1, int jarg2);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_DDirectoryVector_Reverse__SWIG_0")]
  public static extern void DDirectoryVector_Reverse__SWIG_0(HandleRef jarg1);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_DDirectoryVector_Reverse__SWIG_1")]
  public static extern void DDirectoryVector_Reverse__SWIG_1(HandleRef jarg1, int jarg2, int jarg3);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_DDirectoryVector_SetRange")]
  public static extern void DDirectoryVector_SetRange(HandleRef jarg1, int jarg2, HandleRef jarg3);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_DDirectoryVector_Contains")]
  public static extern bool DDirectoryVector_Contains(HandleRef jarg1, HandleRef jarg2);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_DDirectoryVector_IndexOf")]
  public static extern int DDirectoryVector_IndexOf(HandleRef jarg1, HandleRef jarg2);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_DDirectoryVector_LastIndexOf")]
  public static extern int DDirectoryVector_LastIndexOf(HandleRef jarg1, HandleRef jarg2);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_DDirectoryVector_Remove")]
  public static extern bool DDirectoryVector_Remove(HandleRef jarg1, HandleRef jarg2);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_delete_DDirectoryVector")]
  public static extern void delete_DDirectoryVector(HandleRef jarg1);

  [DllImport("ccdb_csllapi", EntryPoint="CSharp_DMySQLDataProvider_SWIGUpcast")]
  public static extern IntPtr DMySQLDataProvider_SWIGUpcast(IntPtr jarg1);
}

}
