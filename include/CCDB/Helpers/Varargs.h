#ifndef Varargs_h__
#define Varargs_h__

#if defined(sparc) && defined(__CC_ATT301__)

   extern "C" __builtin_va_arg_incr(...);
   typedef char *va_list;
#   define va_end(ap)
#   define va_start(ap, parmN) ap= (char*)(&parmN+1)
#   define va_arg(ap, mode) ((mode*) __builtin_va_arg_incr((mode*)ap))[0]
#   define va_(arg) __builtin_va_alist

#   include <stdio.h>

   extern "C" {
      int vfprintf(FILE*, const char *fmt, va_list ap);
      char *vsprintf(char*, const char *fmt, va_list ap);
   };

#else
#   ifndef __CINT__ 	 
#   include <stdarg.h>
#   endif
#   if defined(sparc) && !defined(__GNUG__) && !defined(__CC_SUN21__) && !defined(__SVR4)
#      define va_(arg) __builtin_va_alist
#   else
#      define va_(arg) arg
#   endif

#endif

#if !defined(D__VA_COPY)
#  if defined(__GNUC__) && !defined(__FreeBSD__)
#     define D__VA_COPY(to, from) __va_copy((to), (from))
#  elif defined(__va_copy)
#     define D__VA_COPY(to, from) __va_copy((to), (from))
#  elif defined(va_copy)
#     define D__VA_COPY(to, from) va_copy((to), (from))
#  elif defined (D__VA_COPY_AS_ARRAY)
#     define D__VA_COPY(to, from) memmove((to), (from), sizeof(va_list))
#  elif defined(_WIN32) && _MSC_VER < 1310
#     define D__VA_COPY(to, from) (*(to) = *(from))
#  else
#     define D__VA_COPY(to, from) ((to) = (from))
#  endif
#endif


#endif //!Varargs_h__
