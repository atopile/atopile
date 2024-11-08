use pyo3::prelude::*;

mod ast;
mod error;
mod parser;
mod python;
mod utils;

#[cfg(test)]
mod tests;

// Re-export only what's needed for the public API
pub use ast::*;
pub use error::*;
pub use parser::parse_file; // Only expose the main parsing function
pub use python::*;

/// A Python module implemented in Rust.
#[pymodule]
fn ato_parser(_py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    // Register the parser function
    m.add_function(wrap_pyfunction!(parse_file_py, m)?)?;
    Ok(())
}

#[pyfunction]
fn parse_file_py(py: Python<'_>, content: &str) -> PyResult<PyObject> {
    match parser::parse_file(content) {
        Ok(ast) => Ok(ast.into_py(py)),
        Err(e) => Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))
    }
}
