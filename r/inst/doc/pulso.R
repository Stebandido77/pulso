## ----include = FALSE----------------------------------------------------------
knitr::opts_chunk$set(
  collapse = TRUE,
  comment = "#>",
  eval = TRUE
)

## ----eval=FALSE---------------------------------------------------------------
# library(pulso)
# 
# # 2024-06 is a validated period -- loads without any warning
# df <- pulso_load(year = 2024, month = 6, module = "ocupados")

## ----eval=FALSE---------------------------------------------------------------
# # Raises pulso_data_not_validated -- 2024-09 is not yet validated
# df <- pulso_load(year = 2024, month = 9, module = "ocupados")
# 
# # Explicitly allow unvalidated periods -- emits a visible warning
# df <- pulso_load(year = 2024, month = 9, module = "ocupados",
#                  allow_unvalidated = TRUE)

## ----eval=FALSE---------------------------------------------------------------
# pulso_validation_status(2024, 6)

## ----eval=FALSE---------------------------------------------------------------
# pulso_list_validated_range()

## ----eval=FALSE---------------------------------------------------------------
# df <- pulso_load(year = 2024, month = 6, module = "ocupados",
#                  metadata = TRUE)

## ----eval=FALSE---------------------------------------------------------------
# cat(pulso_describe_column(df, "p6020"))

## ----eval=FALSE---------------------------------------------------------------
# metadata_summary <- pulso_list_columns_metadata(df)
# print(metadata_summary)

## -----------------------------------------------------------------------------
library(pulso)
vars <- pulso_list_variables()
head(vars[, c("canonical_name", "module", "has_warning")], 10)

## -----------------------------------------------------------------------------
cat(pulso_describe_variable("sexo"))

## -----------------------------------------------------------------------------
cat(pulso_describe("ocupados"))

## ----eval=FALSE---------------------------------------------------------------
# # R
# library(pulso)
# df <- pulso_load(year = 2024, month = 6, module = "ocupados",
#                  metadata = TRUE)
# cat(pulso_describe_column(df, "p6020"))

