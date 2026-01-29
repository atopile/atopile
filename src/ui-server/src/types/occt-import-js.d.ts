declare module 'occt-import-js' {
  interface OcctMesh {
    name: string
    color?: [number, number, number]
    brep_faces?: { first: number; last: number }[]
    index: { array: number[] }
    attributes: {
      position: { array: number[] }
      normal?: { array: number[] }
    }
  }

  interface OcctResult {
    success: boolean
    meshes: OcctMesh[]
  }

  interface OcctModule {
    ReadStepFile(content: Uint8Array, params: null | object): OcctResult
    ReadBrepFile(content: Uint8Array, params: null | object): OcctResult
    ReadIgesFile(content: Uint8Array, params: null | object): OcctResult
  }

  interface OcctInitOptions {
    locateFile?: (file: string) => string
  }

  export default function occtimportjs(options?: OcctInitOptions): Promise<OcctModule>
}
