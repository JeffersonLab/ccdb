.PHONY: clean All

All:
	@echo ----------Building project:[ Tests - Debug ]----------
	@"$(MAKE)" -f "Tests.mk"
clean:
	@echo ----------Cleaning project:[ Tests - Debug ]----------
	@"$(MAKE)" -f "Tests.mk" clean
