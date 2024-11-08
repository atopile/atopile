mod import_tests;
mod arithmetic_tests;
mod block_tests;
mod physical_tests;
mod statement_tests;
mod error_tests;
mod line_continuation_tests;
mod assignment_tests;
mod mixed_content_tests;

// Re-export test utilities if needed
pub(crate) use import_tests::*;
pub(crate) use arithmetic_tests::*;
pub(crate) use block_tests::*;
pub(crate) use physical_tests::*;
pub(crate) use statement_tests::*;
pub(crate) use error_tests::*;
pub(crate) use line_continuation_tests::*;
pub(crate) use assignment_tests::*;
pub(crate) use mixed_content_tests::*; 