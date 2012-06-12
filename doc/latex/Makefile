OBJS = rezest.o rezest_fdc_cdc.o
EXE = rezest_point rezest_point_comp
MAINOBJ = $(addsuffix .o, $@)
FFLAGS = -g

all: lib $(EXE)

lib: $(OBJS)
	ar rcv librezest.a $(OBJS)

cdc: $(OBJS) cdc.o
	$(FC) -o $@ $(MAINOBJ) -L. -lrezest

combined: $(OBJS) combined.o
	$(FC) -o $@ $(MAINOBJ) -L. -lrezest

rezest_point: $(OBJS) rezest_point.o
	$(FC) -o $@ $(MAINOBJ) -L. -lrezest

rezest_point_comp: $(OBJS) rezest_point_comp.o
	$(FC) -o $@ $(MAINOBJ) -L. -lrezest

rezest.pdf: ccdb_doc.tex ccdb_doc.bib \
		CDC_geometry.png FDC_geometry.png $(wildcard figure/*.png)
	pdflatex rezest
	bibtex rezest
	pdflatex rezest
	pdflatex rezest

%.png: %.fig
	fig2dev -L png $< $@

# end of makefile
