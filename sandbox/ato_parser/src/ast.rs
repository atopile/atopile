use pyo3::prelude::*;
use pyo3::types::PyDict;

#[derive(Debug, Clone, PartialEq)]
pub enum Statement {
    Import(ImportStmt),
    Assignment(AssignmentStmt),
    Connection(ConnectionStmt),
    Block(BlockStmt),
    Declaration(DeclarationStmt),
    Pass,
    DocString(String),
    Comment(String),
    Assert(AssertStmt),
    Retype(RetypeStmt),
    SignalDef(String),
    PinDef(PinIdentifier),
    CumulativeAssign(CumulativeAssignStmt),
    SetAssign(SetAssignStmt),
    PhysicalQuantity(PhysicalQuantity),
    BilateralQuantity(BilateralQuantity),
}

#[derive(Debug, Clone, PartialEq)]
pub enum ImportStmt {
    FromImport { module: String, items: Vec<String> },
    DirectImport { module: String },
    FromStringImport { path: String, items: Vec<String> },
}

#[derive(Debug, Clone, PartialEq)]
pub struct BlockStmt {
    pub block_type: BlockType,
    pub name: String,
    pub parent: Option<String>,
    pub body: Vec<Statement>,
}

#[derive(Debug, Clone, PartialEq)]
pub enum BlockType {
    Component,
    Module,
    Interface,
}

#[derive(Debug, Clone, PartialEq)]
pub enum Operator {
    Add,
    Subtract,
    Multiply,
    Divide,
    Power,
    BitwiseOr,
    BitwiseAnd,
    BitwiseXor,
    LeftShift,
    RightShift,
    LessThan,
    GreaterThan,
    LessEqual,
    GreaterEqual,
    Equal,
    NotEqual,
    Within,
    Plus,
    Minus,
    Not,
    At,
    Arrow,
}

#[derive(Debug, Clone, PartialEq)]
pub struct BilateralQuantity {
    pub value: f64,
    pub unit: Option<String>,
    pub tolerance: Box<Tolerance>,
}

#[derive(Debug, Clone, PartialEq)]
pub enum Tolerance {
    Percentage(f64),
    Absolute(Box<BilateralQuantity>),
}

#[derive(Debug, Clone, PartialEq)]
pub struct PhysicalQuantity {
    pub value: f64,
    pub unit: Option<String>,
}

#[derive(Debug, Clone, PartialEq)]
pub enum Expression {
    String(String),
    Number(f64),
    Boolean(bool),
    Identifier(String),
    Physical(PhysicalQuantity),
    Bilateral(BilateralQuantity),
    BinaryOp(Box<Expression>, Operator, Box<Expression>),
    UnaryOp(Operator, Box<Expression>),
    Group(Box<Expression>),
    New(String),
}

#[derive(Debug, Clone, PartialEq)]
pub enum Connectable {
    Name(String),
    Pin(String),
    Signal(String),
}

#[derive(Debug, Clone, PartialEq)]
pub enum CumulativeValue {
    Physical(PhysicalQuantity),
    Arithmetic(Expression),
}

#[derive(Debug, Clone, PartialEq)]
pub struct AssignmentStmt {
    pub target: String,
    pub operator: AssignmentOperator,
    pub value: Expression,
    pub type_info: Option<String>,
}

#[derive(Debug, Clone, PartialEq)]
pub struct ConnectionStmt {
    pub left: Connectable,
    pub right: Connectable,
}

#[derive(Debug, Clone, PartialEq)]
pub struct DeclarationStmt {
    pub name: String,
    pub type_info: String,
}

#[derive(Debug, Clone, PartialEq)]
pub struct AssertStmt {
    pub condition: Expression,
}

#[derive(Debug, Clone, PartialEq)]
pub struct RetypeStmt {
    pub source: String,
    pub target: String,
}

#[derive(Debug, Clone, PartialEq)]
pub enum PinIdentifier {
    Name(String),
    Number(i64),
    StringLiteral(String),
}

#[derive(Debug, Clone, PartialEq)]
pub struct CumulativeAssignStmt {
    pub target: String,
    pub operator: AssignmentOperator,
    pub value: CumulativeValue,
    pub type_info: Option<String>,
}

#[derive(Debug, Clone, PartialEq)]
pub struct SetAssignStmt {
    pub target: String,
    pub operator: AssignmentOperator,
    pub value: CumulativeValue,
    pub type_info: Option<String>,
}

#[derive(Debug, Clone, PartialEq)]
pub enum AssignmentOperator {
    Simple,
    Add,
    Subtract,
    Multiply,
    Divide,
    Power,
    IntegerDivide,
    BitwiseOr,
    BitwiseAnd,
    BitwiseXor,
    LeftShift,
    RightShift,
    At,
}

impl Statement {
    pub fn get_type(&self) -> &'static str {
        match self {
            Statement::Import(_) => "Import",
            Statement::Assignment(_) => "Assignment",
            Statement::Connection(_) => "Connection",
            Statement::Block(_) => "Block",
            Statement::Declaration(_) => "Declaration",
            Statement::Pass => "Pass",
            Statement::DocString(_) => "DocString",
            Statement::Comment(_) => "Comment",
            Statement::Assert(_) => "Assert",
            Statement::Retype(_) => "Retype",
            Statement::SignalDef(_) => "SignalDef",
            Statement::PinDef(_) => "PinDef",
            Statement::CumulativeAssign(_) => "CumulativeAssign",
            Statement::SetAssign(_) => "SetAssign",
            Statement::PhysicalQuantity(_) => "PhysicalQuantity",
            Statement::BilateralQuantity(_) => "BilateralQuantity",
        }
    }

    pub fn to_dict(&self, py: Python<'_>) -> PyResult<Py<PyAny>> {
        let dict = PyDict::new_bound(py);
        dict.set_item("type", self.get_type())?;

        match self {
            Statement::Import(import_stmt) => {
                match import_stmt {
                    ImportStmt::FromImport { module, items } => {
                        dict.set_item("module", module)?;
                        dict.set_item("items", items)?;
                    },
                    ImportStmt::DirectImport { module } => {
                        dict.set_item("module", module)?;
                    },
                    ImportStmt::FromStringImport { path, items } => {
                        dict.set_item("path", path)?;
                        dict.set_item("items", items)?;
                    }
                }
            },
            Statement::Block(block) => {
                dict.set_item("block_type", format!("{:?}", block.block_type))?;
                dict.set_item("name", &block.name)?;
                if let Some(parent) = &block.parent {
                    dict.set_item("parent", parent)?;
                }
                dict.set_item("body", &block.body)?;
            },
            Statement::PhysicalQuantity(qty) => {
                dict.set_item("value", qty.value)?;
                if let Some(unit) = &qty.unit {
                    dict.set_item("unit", unit)?;
                }
            },
            Statement::BilateralQuantity(qty) => {
                dict.set_item("value", qty.value)?;
                if let Some(unit) = &qty.unit {
                    dict.set_item("unit", unit)?;
                }
                dict.set_item("tolerance", &*qty.tolerance)?;
            },
            _ => {},
        }

        Ok(dict.into())
    }
}

impl IntoPy<PyObject> for Statement {
    fn into_py(self, py: Python<'_>) -> PyObject {
        self.to_dict(py).unwrap_or_else(|_| py.None())
    }
}

impl ToPyObject for Statement {
    fn to_object(&self, py: Python<'_>) -> PyObject {
        self.clone().into_py(py)
    }
}

impl IntoPy<PyObject> for Tolerance {
    fn into_py(self, py: Python<'_>) -> PyObject {
        let dict = PyDict::new_bound(py);
        match self {
            Tolerance::Percentage(value) => {
                dict.set_item("type", "percentage").unwrap();
                dict.set_item("value", value).unwrap();
            },
            Tolerance::Absolute(qty) => {
                dict.set_item("type", "absolute").unwrap();
                dict.set_item("value", *qty).unwrap();
            }
        }
        dict.into()
    }
}

impl ToPyObject for Tolerance {
    fn to_object(&self, py: Python<'_>) -> PyObject {
        self.clone().into_py(py)
    }
}

impl ToPyObject for BilateralQuantity {
    fn to_object(&self, py: Python<'_>) -> PyObject {
        self.clone().into_py(py)
    }
}

impl IntoPy<PyObject> for PhysicalQuantity {
    fn into_py(self, py: Python<'_>) -> PyObject {
        let dict = PyDict::new_bound(py);
        dict.set_item("value", self.value).unwrap();
        if let Some(unit) = self.unit {
            dict.set_item("unit", unit).unwrap();
        }
        dict.into()
    }
}

impl IntoPy<PyObject> for BilateralQuantity {
    fn into_py(self, py: Python<'_>) -> PyObject {
        let dict = PyDict::new_bound(py);
        dict.set_item("value", self.value).unwrap();
        if let Some(unit) = self.unit {
            dict.set_item("unit", unit).unwrap();
        }
        dict.set_item("tolerance", *self.tolerance).unwrap();
        dict.into()
    }
}

impl IntoPy<PyObject> for BlockStmt {
    fn into_py(self, py: Python<'_>) -> PyObject {
        let dict = PyDict::new_bound(py);
        dict.set_item("block_type", format!("{:?}", self.block_type)).unwrap();
        dict.set_item("name", self.name).unwrap();
        if let Some(parent) = self.parent {
            dict.set_item("parent", parent).unwrap();
        }
        dict.set_item("body", self.body).unwrap();
        dict.into()
    }
}
