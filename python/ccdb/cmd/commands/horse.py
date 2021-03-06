import logging
from ccdb.cmd import CliCommandBase

log = logging.getLogger("ccdb.cmd.commands.horse")


# *********************************************************************
#   Class Horse - Horse                                               *
# *********************************************************************
class Horse(CliCommandBase):
    """ horse """
    
    # ccdb utility class descr part 
    # ------------------------------
    command = "horse"
    name = "Horse"
    short_descr = "Horse"


    # ----------------------------------------
    #   print_help
    # ----------------------------------------
    def print_help(self):
        print ("""Draws horse for your console
        flags are:
            --full      - full sized horse
            --young     - young horse
            --toy       - toy horse
            --solid     - solid looking horse
            --portrait - portrait of a horse
            --funny     - funny horse
            """)

    def execute(self, args):

        horse = self.horse4
        if len(args) > 0:
            if args[0] == "--full":
                horse = self.full_horse
            elif args[0] == "--young":
                horse = self.young
            elif args[0] == "--toy":
                horse = self.toy
            elif args[0] == "--solid":
                horse = self.solid
            elif args[0] == "--portrait":
                horse = self.head
            elif args[0] == "--funny":
                horse = self.horse3
        print (horse)

    full_horse = (r"""
                                                 `T",.`-,
                                                     '8, :.
                                              `""`oooob."T,.
                                            ,-`".)O;8:doob.'-.
                                     ,..`'.'' -dP()d8O8Yo8:,..`,
                                   -o8b-     ,..)doOO8:':o; `Y8.`,
                                  ,..bo.,.....)OOO888o' :oO.  ".  `-.
                                , "`"d....88OOOOO8O88o  :O8o;.    ;;,b
                               ,dOOOOO""'""'""O88888o:  :O88Oo.;:o888d
                               ""888Ob...,-- :o88O88o:. :o'""'""'"Y8OP
                               d8888.....,.. :o8OO888:: ::
                              "" .dOO8bo`'',,;O88O:O8o: ::,
                                 ,dd8".  ,-)do8O8o:"'"; :::
                                 ,db(.  T)8P:8o:::::    :::
                                 -"",`(;O"KdOo::        :::
                                   ,K,'".doo:::'        :o:
                                    .doo:::"'"::  :.    'o:
        ,..            .;ooooooo..o:""'""     ::;. ::;.  'o.
   ,, "'    ` ..   .d;o:"'"'                  ::o:;::o::  :;
   d,         , ..ooo::;                      ::oo:;::o"'.:o
  ,d'.       :OOOOO8Oo::" '.. .               ::o8Ooo:;  ;o:
  'P"   ;  ;.OPd8888O8::;. 'oOoo:.;..         ;:O88Ooo:' O"'
  ,8:   o::oO` 88888OOo:::  o8O8Oo:::;;     ,;:oO88OOo;  '
 ,YP  ,::;:O:  888888o::::  :8888Ooo::::::::::oo888888o;. ,
 ',d: :;;O;:   :888888::o;  :8888888Ooooooooooo88888888Oo; ,
 dPY:  :o8O     YO8888O:O:;  O8888888888OOOO888"" Y8o:O88o; ,
,' O:  'ob`      "8888888Oo;;o8888888888888'"'     `8OO:.`OOb .
'  Y:  ,:o:       `8O88888OOoo""'""'""'""'           `OOob`Y8b`
   ::  ';o:        `8O88o:oOoP                        `8Oo `YO.
   `:   Oo:         `888O::oP                          88O  :OY
    :o; 8oP         :888o::P                           do:  8O:
   ,ooO:8O'       ,d8888o:O'                          dOo   ;:.
   ;O8odo'        88888O:o'                          do::  oo.:
  d"`)8O'         "YO88Oo'                          "8O:   o8b'
 ''-'`"            d:O8oK  -hrr-                   dOOo'  :o":
                   O:8o:b.                        :88o:   `8:,
                   `8O:;7b,.                       `"8'     Y:
                    `YO;`8b'
                     `Oo; 8:.
                      `OP"8.`
                       :  Y8P
                       `o  `,
                        Y8bod.
                        `""'"'
""")
    full_horse2 = r"""

                                                          ,   .
                                                      ___/J-._
                                                    -"   L    ~
                                                  -"      '  ; \\
                                                 "       /   `r,\ .
                                                /       |        \\
                                               /        \       ;.\\
                                               |         f"-_ "" ' \\
                                               |       :  \  ',,-. bj
                                               |       : : \   L`]_/
                                               |      "'"; :\:  "
                                               |   ::::      \\
                                               |o::        :: \\
                                              /:::'        :o |
                                             /               - -
                                            /               _ |_\\
            _,,,--._                     _."        :  :.  / 'x  \\
          ," ,..    "-,              _,-"          ::;. :: .  |  |
        ,, "'    `~..  )    __,---"'"              :          |  L____
        d,         ,).(__,-"                              L   |-,     "'"--"",
       ,d'.       :OO\   ,     '.. .                      7 _ L     __,,,_   |
       'P"   ;  ;.OP/ ,-"  ::;.          .               / _ (-""'""      T  J
       ,8:   o::oO`  /        :         ::;;     ,;:oO88(    "\           / /
      ,YP  ,::;:O:   |        .     (   ".:::::::::oo888 \     \         / /
      ',d: :;;O;:    |888::    ;;;   "-,  \ooooooooo88__, ",_   \      ,/ /
      dPY:  :o8O     |O8888O:O:; ;;;    " |       _,""      ",   \-,,_  \\
     ,' O:  'ob`      |8888888Oo;        |__,,--""            ",  \   |  |
     '  Y:  ,:o:       L,___            _j                      j  "  l -"
        ::  ';o:            \       _,-"                        \   \\
        `:   Oo:             J / ,-"                             "._ j
         :o; 8oP            /  :/                                   \ \\
        ,ooO:8O'          /" o:/                                     \ \\
        ;O8odo'           L_(_|L                                      \ \\
       d"`)8O'              -,, "-._                                   \ "-,
      ''-'`"                   ""-,_, "",                               L__ '-,
                                    "-j  \                                 L   \\


                                                          ,   .
                                                      ___/J-._
                                                    -"   L    ~
                                                  -"      '  ; \\
                                                 "       /   `r,\ .
                                                /       |        \\
                                               /        \       ;.\\
                                               |         f"-_ "" ' \\
                                               |       :  \  ',,-. bj
                                               |       : : \   L`]_/
                                               |      "'"; :\:  "
                                               |   ::::      \\
                                               |o::        :: \\
                                              /:::'        :o |
                                             /               - -
                                            /                 !_\\
            _,,,--._                     _."        :  :.  .-'x  \\
          ," ,..    "-,              _,-"          ::;. ::    |  |
        ,, "'    `~..  )    __,---"'"              :          |  L____
         ,         ,).(__,-"                               | _|-,     "'"--"",
       , '.       :  \   ,     '.. .                      7 _  /    __,,,_   |
       ' "   ;  ;.    ,-"  ::;.          .                 _  L""'""      T  J
       , :    ::  `  /        :                         (    ""-,,_       / /
      ,    ,::;: :   |        .     (   ".:              \         ""-----./
      ', : :;; ;:    |         ;;;   "-,              __, ""--,,,,,,,__   |
            :(       |        :; ;;;    ".        _,""                _l  J
     ,'  :  ' )`      |         ;        |--,,--""                   | T /
     '   :  ,: :       L,___            _j                           l/ /
        ::  '  :            \       _,-"                             / /
        `:     :             J / ,-"                              _," /
         : ;                / /:/                               /    /
        ,      '          /" o:/                               /_,"'"
        ;     '           L_(_l\
         `)  '              -,, "-._
      ''-'`"                   ""-,_"'"",
                                    "-L  \\

"""

    horse3 = r"""
           .  ,
           |\/|
           bd "n.
          /   _,"n.___.,--x.
         <co>'\             Y
          ~~   \       L   7|
                H l--'~\\ (||
                H l     H |`'
                H [     H [
           ____//,]____//,]___

-Row
"""
    horse4 = r"""
                   ,%%%,
                 ,%%%` %
                ,%%`( '|
               ,%%@ /\_/
     ,%.-"'"--%%% "@@__
    %%/             |__`\\
   .%'\     |   \   /  //
   ,%' >   .'----\ |  [/
      < <<`       ||
       `\\\       ||
         )\\      )\\
 ^^^jgs^^"'"^^^^^^""^^^^^^^^^^^
 """
    young = r"""
                               _(\_/)
                             ,((((^`\\
                            ((((  (O \\
                          ,((((( ,    \\
      ,,,_              ,(((((  /"._  ,`,
     ((((\\ ,...       ,((((   /    `-.-'
     )))  ;'    `"'"'""((((   (
    (((  /            (((      \\
     )) |                      |
    ((  |        .       '     |
    ))  \     _ '      `t   ,.')
    (   |   y;- -,-""'"-.\   \/
    )   / ./  ) /         `\  \\
       |./   ( (           / /'
       ||     \\\          //'|  
   jgs ||      \\\       _//'||  
       ||       ))     |_/  ||  
       \_\     |_/          ||  
       `'"                  \_\\
                            `'"
"""
    head = r"""

                      ~~%%%%%%%%_,_,
                   ~~%%%%%%%%%-"/./
                 ~~%%%%%%%-'   /  `.
              ~~%%%%%%%%'  .     ,__;
            ~~%%%%%%%%'   :       \O\\
          ~~%%%%%%%%'    :          `.
       ~~%%%%%%%%'       `. _,        '
    ~~%%%%%%%%'          .'`-._        `.
 ~~%%%%%%%%%'           :     `-.     (,;
~~%%%%%%%%'             :         `._\_.'
~~%%jgs%%'              ;


"""

    toy = r"""

              /\,%,^
              \%%%/,\\
            _.-"%%|//%
          .'  .-"  /%%%
      _.-'_.-" 0)   \%%%
     /.\.'           \%%%
     \ /      _,      %%%
      `"---"~`\   _,*'\%%'   _,--""'"-,%%,
               )*^     `""~~`          \%%%,
             _/                         \%%%
         _.-`/                           |%%,___
     _.-"   /      ,           ,        ,|%%   .`\\
    /\     /      /             `\       \%'   \ /
    \ \ _,/      /`~-._         _,`\      \`""~~`
     `"` /-.,_ /'      `~"----"~    `\     \\
   jgs   \___,'                       \.-"`/
                                       `--'
"""
    solid = r"""

   Yb,     ________
    Y8baad8888888888ba,_
 aaad88888888888888888888b,
 `Y8888888888888888888888888b,
   `"8888888888888888888888888ba,
     Y888( )888888888888888888888ba,
     `Y888888888888888888888888888888ba,________,,aaddddbbbaa,,____,aaa,
      `Y88888888888888888888888888888888888888888888888888888888888888888b,
        Y88888888'888888888888888888888888888888888888888888888888888=88888b
        `88888888 88888888888888888888888888888888888888888888888888888=8888I
         Y8"88888 888888888888888888888888888888888888888888888888888888=888b
          Y88888P 888888888888888888888888888888888888888888888888888888=8888
           `""'"  Y88888888888888888888888888888888888888888888888888888=8888
                  (88888888888888888888888888888888888888888888888888888=8888
                  `88888888888888888888888888888888888888888888888888888=888(
                   `888888888888888888888888888888888888888888888888888=8888I
                    d88888888888888888888888888888888888888888888888888=8888I
                  ,d888888PY88888888888P"Y888888P"88888888888888888888=88888(
                 d888888P'  Y8888888888'           888888888888888888=8888888
                d88888P"    `Y888888888            I8888888"Y88888888=8888888
               d88888(,      `Y8888888P            `888888P  `Y888888 Y88888P
               `Y88888b,      `Y888888I             888888'   `888888  `""'"
                 `Y88888b,  __ `888888'            ,88888P     888888
                   `Y88888bd88b `88888             I88888'     Y88888
                     `Y88888888b 88888             88888P      `88888
            Normand    `Y888888888888P            d8888P'       88888,
            Veilleux      `""'",d8888I        ,ad888888'        Y8888I
                            ,a8888888'       d888888P'         ,d88888
                           d8888888'         88888888       ,d8888888P
                           88888888                         88888888'
                                                            ""'""'""
"""

    more = r"""


   Yb,     ________
    Y8baadP""'""'""Yba,_
 aaadP"'             `""Yb,
 `Y8(                    `"Yb,
   `Y,                      `Yba,
     Y,  (O)                   `Yba,
     `Y,                          ""Yba,________,,aaddddbbbaa,,____,aa,_
      `Y,       ,aa                   `""'""'""'"''          ``""'"''  "Y,
        Y,      d'8                                                "Ya   `Y,
        `b      8 8                                                  `Y,   Y,
         Ya o  ,8 8                                                    b   `b
          Yb,_,dP 8                                                    Y    8
           `""'"  Y                                                    8    8
                  I,                                                   8    8
                  `b                                                   P    [
                   `b                                                 d'    [
                    d                                                ,P     [
                  ,d'    ,PY,         ,P"YaaaaaaP"Ybaaa,,_           d'     [
                 d"    ,P"  Y,        d'           8'  `""db,       d'      8
                d'   ,P"    `Y,       8            I,     d'"b,     8a      P
               d(    (       `Y,      P            `b    ,P  `Y,    8`Ya___d'
               "Y,   "b,      `Y,    ,I             8    d'   `8    8  `"'"'
                 "Y,   "b,  __ `8,   d'            ,8   ,P     8    8
                   "Y,   "bd88b `b   8             I'   d'     Y,   8
                     "Y,    888b 8   8             8   ,P      `b   8
            Normand    "Ya,,d888b8   P            d'  ,P'       8   Y,
            Veilleux      `""'",d"  ,I        ,adPb__aP'        Y   `b
                            ,a8P,__aP'       d888888P'         ,d    8
                           d8888888'         88888888       ,d888bbaaP
                           88888888                         88888888'
                                                            ""'""'""
"""