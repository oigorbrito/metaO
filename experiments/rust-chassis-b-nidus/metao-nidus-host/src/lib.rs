use nidus_core::{ModuleBuilder, ModuleGraph, NidusError};

pub fn valid_host_graph() -> Result<ModuleGraph, NidusError> {
    let kernel = ModuleBuilder::new("MetaOKernelModule")
        .provider("MetaOKernelService")
        .export("MetaOKernelService")
        .build();
    let adapters = ModuleBuilder::new("RuntimeAdaptersModule")
        .import("MetaOKernelModule")
        .provider("RuntimeRegistry")
        .build();
    ModuleGraph::from_modules([kernel, adapters])
}

pub fn circular_host_graph() -> Result<ModuleGraph, NidusError> {
    let kernel = ModuleBuilder::new("MetaOKernelModule")
        .import("RuntimeAdaptersModule")
        .build();
    let adapters = ModuleBuilder::new("RuntimeAdaptersModule")
        .import("MetaOKernelModule")
        .build();
    ModuleGraph::from_modules([kernel, adapters])
}

pub fn ambiguous_provider_graph() -> Result<ModuleGraph, NidusError> {
    let a = ModuleBuilder::new("AdapterA")
        .provider("RuntimePort")
        .export("RuntimePort")
        .build();
    let b = ModuleBuilder::new("AdapterB")
        .provider("RuntimePort")
        .export("RuntimePort")
        .build();
    let root = ModuleBuilder::new("MetaOHost")
        .import("AdapterA")
        .import("AdapterB")
        .build();
    ModuleGraph::from_modules([a, b, root])
}
