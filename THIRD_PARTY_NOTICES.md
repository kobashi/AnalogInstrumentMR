# Third-party notices

This repository contains original project code and assets. Unity, Meta XR SDK,
MR Utility Kit, OpenXR packages, Blender, and their transitive dependencies are
not relicensed by this project. They are obtained separately and remain subject
to their own license terms.

## Meta XR packages

Unity Package Manager resolves these direct dependencies at version `203.0.0`:

- `com.meta.xr.mrutilitykit`
- `com.meta.xr.sdk.core`
- `com.meta.xr.sdk.interaction`

Copyright © Meta Platforms, Inc. and affiliates. These packages are licensed
under the [Meta/Oculus SDK License Agreement][meta-sdk-license], not this
repository's MIT or CC BY license. Preserve the `LICENSE` and `NOTICE` files
supplied with each package if you redistribute material permitted by that
license.

## Unity Editor and packages

The project was verified with Unity `6000.3.19f1`. Direct Unity package
dependencies and exact versions are recorded in `Packages/manifest.json` and
`Packages/packages-lock.json`. Unity packages may use the Unity Companion
License, Unity Package Distribution License, MIT License, or another license
identified in each downloaded package.

The Unity Editor and `com.unity.modules.*` components are Unity products and
are not included in this repository's license grant. Review the license files
installed with every package before redistribution:

- [Unity Companion License][unity-companion]
- [Unity Package Distribution License][unity-distribution]
- [Unity Terms of Service][unity-terms]

## Blender

Blender is an external authoring tool and is not distributed in this
repository. The Python scripts under `Tools/Blender/` use Blender's `bpy` API
to procedurally create the original project models, textures, and previews.
Blender is available under the GNU General Public License from
[blender.org][blender].

## Trademarks and affiliation

Meta, Quest, Unity, Blender, and other names are trademarks of their respective
owners. Use of those names identifies compatibility or tooling only and does
not imply endorsement.

[meta-sdk-license]: https://developers.meta.com/horizon/licenses/oculussdk/
[unity-companion]: https://unity.com/legal/licenses/unity-companion-license
[unity-distribution]: https://unity.com/legal/licenses/unity-package-distribution-license
[unity-terms]: https://unity.com/legal/terms-of-service
[blender]: https://www.blender.org/about/license/
