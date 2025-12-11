declare module 'react-router-dom' {
  import * as React from 'react'
  export interface RouterProviderProps { router: any }
  export const RouterProvider: React.FC<RouterProviderProps>
  export function createBrowserRouter(routes: any, opts?: any): any
}


