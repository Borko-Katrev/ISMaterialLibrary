# ISMaterialLibrary

This library groups shaders by the projects they were created in. It gives quick acces to shaders relevant to the current project.
It also allows for the sorting of shaders by their material properties and searching by name. When exporting one has the opportunity to copy and relink all
connected textures to the location of the shader. A whole project group with all shaders in it can be copied to a different location for backup purposes.
Descriptions of shaders cann be added or changed at any time. One can also overrite and export/import multiple versions of a material.
To use it one must:
1. Copy the script in "Documents\maya\(maya version)\scripts" and create an empty text file called ISMLconfig.txt.
2. Make another empty ISMLconfig file somewhere on the system. One of the config files is supposed to be on a shared location, the whole team has access to. The one
in documents can be used for personal work.
3. On lines 20 and 21 change the paths "/maya/2020/scripts/ISMLconfig.txt" and "O:/Maya/MayaScripts/ISML/ISMLconfig.txt" to the locations of your config files.
4. In Maya write the following python script and save it in a shelf.
import ISML
reload(ISML)
