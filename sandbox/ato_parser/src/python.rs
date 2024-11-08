use pyo3::prelude::*;

use crate::ast::*;

#[pyclass]
#[derive(Debug)]
pub struct AtopileError {
    #[pyo3(get)]
    message: String,
    #[pyo3(get)]
    line: usize,
    #[pyo3(get)]
    column: usize,
    #[pyo3(get)]
    context: String,
    #[pyo3(get)]
    snippet: String,
}

#[pymethods]
impl AtopileError {
    fn __str__(&self, _py: Python<'_>) -> PyResult<String> {
        Ok(format!("{} at line {}, column {}", self.message, self.line, self.column))
    }
}

#[pyclass]
#[derive(Debug)]
pub struct AtoAST {
    statements: Vec<Statement>,
}

#[pymethods]
impl AtoAST {
    fn get_physical_quantities(&self, py: Python<'_>) -> PyResult<Vec<Py<PyAny>>> {
        let mut quantities = Vec::new();
        for stmt in &self.statements {
            if let Statement::PhysicalQuantity(qty) = stmt {
                quantities.push(qty.clone().into_py(py));
            }
        }
        Ok(quantities)
    }

    fn get_bilateral_quantities(&self, py: Python<'_>) -> PyResult<Vec<Py<PyAny>>> {
        let mut quantities = Vec::new();
        for stmt in &self.statements {
            if let Statement::BilateralQuantity(qty) = stmt {
                quantities.push(qty.clone().into_py(py));
            }
        }
        Ok(quantities)
    }

    fn get_blocks(&self, py: Python<'_>) -> PyResult<Vec<Py<PyAny>>> {
        let mut blocks = Vec::new();
        for stmt in &self.statements {
            if let Statement::Block(block) = stmt {
                blocks.push(block.clone().into_py(py));
            }
        }
        Ok(blocks)
    }

    fn to_dict(&self, py: Python<'_>) -> PyResult<Py<PyAny>> {
        let dict = pyo3::types::PyDict::new_bound(py);

        let statements: Vec<PyObject> = self.statements.iter()
            .map(|stmt| stmt.clone().into_py(py))
            .collect();

        dict.set_item("statements", statements)?;
        Ok(dict.into())
    }
}

#[pyfunction]
pub fn parse_atopile(py: Python<'_>, code: &str) -> PyResult<Py<AtoAST>> {
    match crate::parser::parse_statements(code) {
        Ok((_, statements)) => {
            let ast = AtoAST { statements };
            Py::new(py, ast)
        },
        Err(_) => {
            let ast = AtoAST { statements: Vec::new() };
            Py::new(py, ast)
        }
    }
}

#[pymodule]
fn ato_parser(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<AtoAST>()?;
    m.add_class::<AtopileError>()?;
    m.add_function(wrap_pyfunction!(parse_atopile, m)?)?;
    Ok(())
}
