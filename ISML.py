import os
from shutil import copytree, rmtree, copy
from functools import partial

import pymel.core as pm
import maya.cmds as cmds
import maya.mel as mel


# Global variables
iconButtons = []
deleteOptions = []
iconlessButtons = []
globalDirectoryList = []
dirSetSh = set()
dirSetLoc = set()


# Open the config file and get dir list.
docDirLok = "%s/maya/2020/scripts/ISMLconfig.txt" % os.environ.get("HOME")
docDirShared = "O:/Maya/MayaScripts/ISML/ISMLconfig.txt"

with open(docDirShared, "r") as configFileShared:  # Get paths from the shared config file in Addons.
    for line in configFileShared:
        if not line.startswith("#"):
            if line.strip() != "":
                line = line.strip()
                splitIn = line.find("# ")
                dirSetSh.add((line[splitIn+2 :], line[: splitIn]))

with open(docDirLok, "r") as configFileLokal:  # Get paths from the local config file.
    for line in configFileLokal:
        if not line.startswith("#"):
            if line.strip() != "":
                line = line.strip()
                splitIn = line.find("# ")
                dirSetLoc.add((line[splitIn+2 :], line[: splitIn]))


# Merge paths
for both in dirSetSh.intersection(dirSetLoc):
    both = list(both)
    both.append("Both")
    globalDirectoryList.append(both)

for shared in dirSetSh.difference(dirSetLoc):
    shared = list(shared)
    shared.append("Shared")
    globalDirectoryList.append(shared)

for local in dirSetLoc.difference(dirSetSh):
    local = list(local)
    local.append("Local")
    globalDirectoryList.append(local)


""" The following functions are for copying textures to the material folder
and renaming texture nodes inside the .ma file.
"""


# Copy textures to shader dir
def copyTexturesToShaderDir(oldPath, newPath):
    try:
        copy(oldPath, newPath)
        return True
    except Exception as ex:
        pm.warning("%s cannot be copied! :\n%s" % (os.path.basename(oldPath), ex))
    return False


# Get all texture paths from a .ma file
def copyAndLinkTexturesInMaFile(maFile, newTextureDirPath):
    with open(maFile, "r") as mf:
        writeNew = False
        newNodeLines = []
        
        # Get index of all lines starting with "createNode"
        i = 0
        lines = mf.readlines()
        for line in lines:
            if line.startswith("createNode"):
                newNodeLines.append(i)
            i += 1
            
        # Find the end of the last "createNode"
        for line in lines[newNodeLines[-1]+1 :]:
            if not line.startswith("	"):
                newNodeLines.append(lines.index(line))
                break

        for i in range(len(newNodeLines)-1):
            ndLine = newNodeLines[i]
            nextNdLine = newNodeLines[i+1]
            if lines[ndLine][:15] == "createNode file":
                for line in lines[ndLine+1 :nextNdLine]:
                    if line.find('setAttr ".ftn"') != -1:
                        pathStarti = line[:-3].rfind('"') + 1
                        oldTexturePath = line[pathStarti:-3]
                        newTexturePath = os.path.join(newTextureDirPath, os.path.basename(oldTexturePath)).replace("\\","/")
                        if copyTexturesToShaderDir(oldTexturePath, newTexturePath):
                            writeNew = True
                            lnIndex = lines.index(line)
                            lines[lnIndex] = line.replace(oldTexturePath, newTexturePath)
    if writeNew:
        with open(maFile, "w") as wmf:
            for line in lines:
                wmf.write(line)
    else: 
        pm.warning("No textures found in .ma scene. No changes will be written.")


def copyAndReplaceTexturesSingleFile(shaderPath, *args):
    shaderDir = os.path.dirname(shaderPath)
    
    # Make texture folder in the shader folder if it doesnt exist.
    texturePath = "%s/textures" % shaderDir
    if not os.path.exists(texturePath):
        os.mkdir(texturePath)
    copyAndLinkTexturesInMaFile(shaderPath, texturePath)


def copyAndReplaceTextures(iconButtons, *args):
    for iconButton in iconButtons:
        shaderPath = iconButton.getDocTag().split("\n")[-1]
        shaderDir = os.path.dirname(shaderPath)
        
        # Same as in the function above
        texturePath = "%s/textures" % shaderDir
        if not os.path.exists(texturePath):
            os.mkdir(texturePath)
        copyAndLinkTexturesInMaFile(shaderPath, texturePath)


def MoveAllTexturesHandler(*args):
    copyAndReplaceTextures(iconButtons)


""" Given a path the following function, goes trough all of the paths folders and ignores files. Then goes trough all found folders
and if they contain a maya scene file, saves it in a list. Additionaly, if a png image is found, then it is also stored in a list to be used as an icon.
"""

def updatePathList(shaderDirDefaultPath):
    mtlPathList = []
    mtlIconPathList = []
    
    # Get all directories inside path
    try:
        shaderDirs = os.listdir(shaderDirDefaultPath)
    except Exception as ex:
        pm.warning("Path %s was not found! :%s" % (shaderDirDefaultPath, ex))
        shaderDirs = []
    
    for dirName in shaderDirs:
        mtlDir = os.path.join(shaderDirDefaultPath,dirName)  # Gets folder with material and icon
        if os.path.isdir(mtlDir):
            mtlFiles = sorted(os.listdir(mtlDir))  # Gets material and icon
            if len(mtlFiles)>0:
                mtl = []
                mtlIcon = "blinn.svg"
                for mtlFileName in mtlFiles:
                    mtlFilePath = os.path.join(mtlDir,mtlFileName)
                    if os.path.isfile(mtlFilePath):
                        if os.path.splitext(mtlFilePath)[1] == '.ma' or os.path.splitext(mtlFilePath)[1] == '.mb':
                            mtl.append(mtlFilePath)
                        if os.path.splitext(mtlFilePath)[1] == '.png':
                            mtlIcon = mtlFilePath
                if mtl != []:
                    mtlPathList.append(mtl)
                    mtlIconPathList.append(mtlIcon)
    return [mtlPathList, mtlIconPathList]


# Write MaterialTag on the second line of the ma file.
def rewriteWithTag(shaderPath, tag):
    with open(shaderPath, "r") as shaderFile:
                    f = shaderFile.readlines()
                    splitLine = 1
                    if f[1][:14] == "//MaterialTag:":
                        splitLine = 2   
                    with open(shaderPath, "w") as newFile:
                        newFile.write(f[0])
                        newFile.write("//MaterialTag: %s\n" % tag)
                        for line in f[splitLine:]:
                            newFile.write(line)


# Write a comment in the ma file.
def rewriteWithComment(shaderPath, comment):
    comment = comment.replace("\n", "__nwlne__")
    with open( shaderPath , "r" ) as shaderFile:
                    f = shaderFile.readlines()
                    splitLine = 2
                    if f[2][:9] == "//ShComm:":
                        splitLine = 3   
                    with open(shaderPath, "w") as newFile:
                        newFile.write(f[0])
                        newFile.write(f[1])
                        newFile.write("//ShComm: %s\n" % comment)
                        for line in f[splitLine:]:
                            newFile.write(line)


""" Following functions are related to UI functionality
"""

# Add shader Tags.
def addTagOptions(parentUI):
    pm.menuItem(l="Undefined", p=parentUI)
    pm.menuItem(l="Metal", p=parentUI)
    pm.menuItem(l="Multilayered/PaintedSurface", p=parentUI)
    pm.menuItem(l="Refractive", p=parentUI)
    pm.menuItem(l="Rubber", p=parentUI)
    pm.menuItem(l="Stone", p=parentUI)
    pm.menuItem(l="Wood", p=parentUI)
    pm.menuItem(l="Paper", p=parentUI)
    pm.menuItem(l="Textile", p=parentUI)
    pm.menuItem(l="Plastic", p=parentUI)
    pm.menuItem(l="Organic", p=parentUI)
    pm.menuItem(l="Volume", p=parentUI)


# Export shader option/tags window
def exportOptionsWindow(*args):
    expOptWindow = createWindow(name="exportOptionsWindow", height= 385, title="Export Shader Options", minb=False, maxb=False, menuBar=False, resizeable=False)
    
    pm.columnLayout(cal="left", cat=["both", 10], cw=520)
    pm.separator(st="none", h= 5)
    
    pm.rowColumnLayout(nc=2)
    pm.text(l="Add Material Type Tag:", w=137)
    pm.optionMenu("expTagOpMenu", w=361)
    addTagOptions("expTagOpMenu")
    pm.setParent('..')
    
    pm.separator(h=10)
    pm.rowColumnLayout(nc=2, cs=([1,10], [2,5]), rs=[3,15])
    pm.text(l="Copy Textures To Shader Location", al="left", w=200)
    pm.checkBox("copyTexturesCheckBox", l="", v=1)
    pm.setParent("..")
    pm.separator(h=10)
    
    pm.separator(h=5, st="none")
    pm.text(l="Comment:")
    
    pm.separator(st="none", h=5)
    commentField = pm.scrollField("ExportCommentField", w=500, h=300)
    pm.separator(st="none", h=5)
    
    def cancelCommand(*args):
        pm.deleteUI('exportOptionsWindow')
        
    def okCommand(*args):
        shaderPath = exportSG()
        opMenuVal = pm.optionMenu("expTagOpMenu",q=True, v=True)
        if opMenuVal != "None":
            rewriteWithTag(shaderPath, opMenuVal)
               
        rewriteWithComment(shaderPath, commentField.getText())
        expOptWindow.delete()
        
    pm.rowColumnLayout(nc=2, cs=([1,10], [2,5]), rs=[3,15], co=[1,"left",330])
    pm.button(l="cancel", w=70, c=partial(cancelCommand))
    pm.button(l="OK", w=70, c= partial(okCommand))
    
    pm.showWindow("exportOptionsWindow")


# Functions related to exporting
def exportWithoutUVChoosers(shaderPath):
    """UVChooser nodes need to be disconnected since they are tied to meshes in the scene
    and will drag these meshes allong when exporting.  Only the Shader nodes must be exported.
    All connections must then be reconnected.
    """
    transformNodes = listNodeTypesFromNetwork(pm.ls(sl=True)[0], "transform")
    tNodesOutputs = set()
    connectionLists = []
    
    # Get all connected outputs of the meshes
    for tNode in transformNodes:
        tNodesOutputs.update(tNode.getShape().outputs())
        
    # Check if any of them are uvChooser nodes. If yes, save their connections to the meshes in connectionLists.
    for shapeNode in tNodesOutputs:
        if shapeNode.type() == "uvChooser":
            connectionLists += pm.listConnections(shapeNode, c=True, d=False, p=True)
    
    # Disconnect all attributes from the connectionLists variable
    for connection in connectionLists:
        pm.disconnectAttr(connection[0])
   
    cmds.file(shaderPath, op="v=0;", typ="mayaAscii", pr=True, es=True)  # Bugged in pymel, so cmds instead.
    
    # Reconnect all disconnected attributes using the connectionLists variable
    for connection in connectionLists:
        pm.connectAttr(connection[1],connection[0])
    
    # If selected, copy all connected textures to shader dir and change all texture node paths
    if pm.checkBox("copyTexturesCheckBox", ex=True):
        if pm.checkBox("copyTexturesCheckBox", q=True, v=True):
            copyAndReplaceTexturesSingleFile(shaderPath)
    else:
        pm.warning("Textures will not be copied to shader location when exporting new version or overriding!")


# Lists all objects of a certan type, that are connected to a node. Is used to get meshes, that have the material assigned.
def listNodeTypesFromNetwork(mainNode, type):
    nodeSet = set()
    for node in mainNode.listConnections():
        if node.type() == type:
            nodeSet.add(node)
    return nodeSet


# Export shader
def exportSG(*args):
    path = pm.fileDialog2(cap="Export Selected SG", fm=0, okc="Export", ff="Maya ASCII(*.ma)")
    
    if path == None:  # is None doesnt work for some reason
        return 0
    else:
        path = path[0] 
        
    # Export shader
    shaderPath = os.path.split(path)
    fileName = os.path.splitext(shaderPath[1])
    shaderDir = os.path.join(shaderPath[0], fileName[0])
    shaderPath = os.path.join(shaderDir, shaderPath[1])

    if not os.path.exists(shaderDir):
        os.mkdir(shaderDir)
    
    exportWithoutUVChoosers(shaderPath)  
   
    # Refresh and exit
    refreshShaderTab()
    return shaderPath


# Read Tags
def readTagLine(iconLink, skipLines=1):  # The tag is written on the second line of the ma file
    with open(iconLink, "r") as mf:
        for skipLn in range(skipLines):
            mf.readline()
        tagLine = mf.readline()
    return tagLine


# Filter by everything
def filterIcons(iconList, project, tag, searchStr):
    for icon in iconList:
        # Get project of material
        projectName = icon[icon.find("__pr_")+5 :]
        # Get tag from the ma file
        iconLink = pm.iconTextButton(icon, q=True, dtg=True).split("\n")[-1]
        tagLine = readTagLine(iconLink).replace("//MaterialTag: ", "").strip("\n")
        # Get name of icon
        iconName = pm.iconTextButton(icon, q=True, l=True)
        
        pm.iconTextButton(icon, e=True, vis=False)
        if projectName == project or project == "All":
            if tagLine == str(tag) or tag == "All":
                if iconName.lower().find(searchStr.lower()) != -1 or searchStr == "":
                    pm.iconTextButton(icon, e=True, vis=True)


# Import shader
def importShader(path, *args):
    importedNodes = cmds.file(path, i=True, mergeNamespaceWithRoot=True, rpr="tprfx", rnn=True)
    shaderNodes = []
    renderLayer = ""
    for node in importedNodes:
        nt = pm.nodeType(node)
        if nt == "script" or nt == "nodeGraphEditorInfo":
            pm.delete(node)
        elif nt == "renderLayer":
            renderLayer = node
        elif nt == "renderLayerManager":
            pass
        else:
            shaderNodes.append(node)
            
    if renderLayer != "":
        pm.delete(renderLayer)
    return shaderNodes


# Import shader and open renaming window if it has a prefix
def importRenameShader(path, *args):
    importedNodes = importShader(path)
    if importedNodes[0].startswith("tprfx_"):
        renamingWindow(importedNodes,"tprfx_")


# Import/Assign shader
def importAssignShader(iconButton, selOverride, *args):  # Uses cmds in some places because of pyMel bug for some commands.
    path = iconButton.getDocTag().split("\n")[-1]
    
    if not selOverride:
        sel = cmds.ls(selection=True)  # Sets doesn't work if its pm
    else:
        sel = selOverride
    importedNodes = importShader(path)
    mtlSG = ""
    
    for node in importedNodes:
        if pm.nodeType(node)== "shadingEngine":
            mtlSG = node
            break
    if sel != []:
        if mtlSG != "":
            cmds.sets(sel, e=True, fe=mtlSG )
        else:
            cmds.warning("No Shading Group found! Make sure that the shader has a Shading Group! Always export the Shading group and not just the shader!")
    else:
        pm.warning("No mesh selected! Material was still imported, but not assigned to anything!")
    
    # Open renaming window if prefix is found.
    if importedNodes[0].startswith("tprfx_"):
        renamingWindow(importedNodes,"tprfx_")


# Renders scene using VFB and saves image in specified path.
def vrRenderOutput(renderPath):
    pm.vrend()
    mel.eval('vray vfbControl -saveimage "%s";' % renderPath)  # This can only be done with mel. May change in newer versions of vRay...


# Assigns shaders to shader ball and renders them.
def assignRenderIcons(toAssign, *args):
    for shader in toAssign:
        importAssignShader(shader, "shaderBall")
        iconPath = os.path.split(shader.getDocTag().split("\n")[-1])
        iName = "%s_icon.png" % os.path.splitext(iconPath[1])[0]
        iconPath = os.path.join(iconPath[0], iName)
        vrRenderOutput(iconPath.replace("\\", "/"))


# Opens a window with all shader versions.
def importOlderVersion(iconButton, *args): 
    versionWindow = createWindow(name="versionWindow", title="Import Older Version", maxb=False, menuBar=False, resizeable=False)
    
    def doubleClickImport(*args):
        importRenameShader(pm.textScrollList("verScrList",q=True, si=True))
    pm.scrollLayout(w=700,h=500)
    pm.text(l="Double click to select:")
    pm.textScrollList("verScrList", w=695, h=483, ams=False, a=iconButton.getDocTag().split("\n"), dcc=partial(doubleClickImport))
    versionWindow.show()


# UI content    
def exportNewVersion(iconButton, override, *args):  # Handles both overwriting and saving new version.
    shaderPath = iconButton.getDocTag().split("\n")
    newestVersion = shaderPath[-1]
    tagLine = readTagLine(newestVersion).strip("\n")
    
    if not override:
        splitPath = os.path.split(newestVersion)
        newName = os.path.splitext(splitPath[1])
        versionNumber = newName[0][-5:]
        newVersionNumber = "_%s" % str(len(shaderPath)+1).zfill(4)
        
        if versionNumber[0] == "_" and versionNumber[1:].isdigit() == True:
            newName = "%s%s" % (newName[0].replace(versionNumber, newVersionNumber), newName[1])
            newestVersion = os.path.join(splitPath[0], newName)
        else:
            newName = "%s%s%s" % (newName[0], newVersionNumber, newName[1])
            newestVersion = os.path.join(splitPath[0], newName)
        shaderPath.append(newestVersion)
        # Update shader icons in "All"
        iconButton.setDocTag("\n".join(shaderPath))
        iconButton.setCommand(partial(importRenameShader, newestVersion))
        pm.iconTextButton(iconButton.shortName(), e=True, dtg="\n".join(shaderPath))
        pm.iconTextButton(iconButton.shortName(), e=True, c=partial(importRenameShader, newestVersion))   
                
    exportWithoutUVChoosers(newestVersion)
    
    if tagLine[:14] == "//MaterialTag:":
        rewriteWithTag(newestVersion, tagLine[15:])


# Delete the whole shader folder or just the icon image

# Delete folder
def deleteShader(iconButton, *args):
    global iconButtons
    
    shaderPath = iconButton.getDocTag().split("\n")[-1]
    shaderDir = os.path.dirname(shaderPath)
    rmtree(shaderDir)
    buttonContent = iconButton.getDocTag()
    for iButton in iconButtons:
        if buttonContent == iButton.getDocTag():
            iconButtons.remove(iButton)
            pm.deleteUI(iButton)

# Delete icon image
def deleteIconFile(iconButton, *args):
    icon = iconButton.getImage()
    if icon == "blinn.svg":
        pm.warning("This shader doesn't have an icon.")
    else:
        try:
            os.remove(icon)
            iconButton.setImage("blinn.svg")
        except Exception as ex:
            pm.warning(ex)


# Shader comment related functions

# Gets the path from the doc tag of the icon button.
def getShPath(iconButton):
    return iconButton.getDocTag().split("\n")[-1]


#Read shader comment
def readComment(iconButton, *args):
    shaderPath = getShPath(iconButton)
    commLine = readTagLine(shaderPath, skipLines=2)
    if commLine[:9] != "//ShComm:":
        return ""
    else:
        return commLine[10:].replace("__nwlne__", "\n")


#Comment window
def commentWindow(iconButton, *args):
    # Get comment text
    commentText = readComment(iconButton)
    # Make comment window UI
    commentWindow = createWindow(name="CommentWindow", title="Comment", minb=False, maxb=False, menuBar=False)
    pm.paneLayout(cn= "horizontal2", ps=[2,100,5], shp=2)
    commentField = pm.scrollField("ShaderCommentField", w=500, h=300)
    pm.formLayout("CommentForm")
    # Commands 
    def cancelCommand(*args):
        pm.deleteUI("CommentWindow")
        
    def okCommand(iconButton,*args):
        if commentField.getText() != commentText:
            rewriteWithComment(getShPath(iconButton), commentField.getText())
        pm.deleteUI("CommentWindow")
    
    
    pm.button("CancelCommentBt" ,l="Cancel", w=70, c=partial(cancelCommand))
    pm.button("OKCommentBt",l="OK", w=70, c=partial(okCommand, iconButton))
    pm.separator("CommentSep", st="none", h=5)
    pm.formLayout("CommentForm", e=True, af=(["OKCommentBt","right",10], ["CommentSep","bottom",0]), ac= ["CancelCommentBt","right",5,"OKCommentBt"])
    pm.showWindow("CommentWindow")
    # Print comment
    commentField.setText(commentText)


# Open Tag Window
def tagWindow(iconButton, *args):
    shaderPath = getShPath(iconButton)
    shaderTag = readTagLine(shaderPath).replace("//MaterialTag: ", "").strip("\n")
    tagWindow = createWindow(name="TagWindow", title="Change Tag", minb=False, maxb=False, menuBar=False, resizeable=False)
    
    pm.columnLayout(cw=520, cat=["both",10])
    pm.separator(st="none", h=10)
    tagOpMenu = pm.optionMenu("tagWindowOptions", w=500)
    addTagOptions("tagWindowOptions")
    pm.optionMenu("tagWindowOptions", e=True, v=shaderTag)
    
    def okCommand(shaderPath,*args):
        rewriteWithTag(shaderPath, tagOpMenu.getValue())
        pm.deleteUI("TagWindow")
    
    pm.separator(st="none", h=10)
    pm.button(l="Change", c=partial(okCommand, shaderPath))
    pm.separator(st="none", h=10)
    pm.showWindow("TagWindow")


# Show project
def showProject(iconButton, *args):
    projectName = iconButton[iconButton.find("__pr_")+5 :]
    showProjectWindow = createWindow(name="ShowProjectWindow", title="Project", height=10, minb=False, maxb=False, menuBar=False, resizeable=False)
    pm.columnLayout()
    pm.textField(tx=projectName, w=200)
    pm.showWindow(showProjectWindow)


def showShaderLocation(iconButton, *args):
    newestShaderVersion=pm.iconTextButton(iconButton, q= True, dtg= True).split("\n")[-1]
    shaderPathWindow= createWindow(name="shaderPathWindow", title="Shader Path", height= 10, minb= False, maxb=False, menuBar= False, resizeable=False)
    pm.columnLayout()
    pm.textField(tx= newestShaderVersion, w= 500)
    pm.showWindow(shaderPathWindow)     


# Creates an icon for a given shader path.
def createShaderIcon(shaderPath=[], iconSize=110, shaderIcon="blinn.svg", addToIconless=True, shaderLabel="", parentLayout="allShadersLayout", addToName=""):
    """ Creates a clickable icon that imports and assigns the shader to the selection, by using the importAssignShader() function.
    The "addToName" variable allows an additional string to be added to the name of the iconTextButton object.
    """
    global iconlessButtons, deleteOptions, iconButtons
        
    shaderName = os.path.splitext(shaderLabel)[0]
    newestShaderVersion = shaderPath[-1]
    dcTag = "\n".join(shaderPath)
    
    iconButtonName = "%sButton__pr_%s" % (shaderName, addToName)
    iconButton = pm.iconTextButton(iconButtonName ,i=shaderIcon, l=shaderName, p=parentLayout, st="iconAndTextVertical", sic=iconSize, w=iconSize, dtg=dcTag, h=iconSize+20, c=partial(importRenameShader, newestShaderVersion), ann=shaderName)
    
    if shaderIcon == "blinn.svg" and addToIconless:
        iconlessButtons.append(iconButton)
    
    iconOptions = pm.popupMenu("iconButtonMenu",p=iconButton)
    pm.menuItem("importAssign",l="Import And Assign", c=partial(importAssignShader, iconButton, False))
    pm.menuItem("importVersion",l="Import Specific Version", c=partial(importOlderVersion, iconButton))
    pm.menuItem("exportNewVersion",l="Export Selected As New Version", c=partial(exportNewVersion, iconButton, False))
    pm.menuItem("overwriteSubMenu",l="Overwrite Shader", sm=True)
    pm.menuItem("overwriteShader",l="Overwrite", c=partial(exportNewVersion, iconButton, True))
    pm.menuItem("showComment", l="Comment", c=partial(commentWindow, iconButton), p=iconOptions)
    pm.menuItem("showTag", l="Change Tag", c=partial(tagWindow, iconButton), p=iconOptions)
    pm.menuItem("showProject", l="Show Project", c=partial(showProject, iconButton), p=iconOptions)
    pm.menuItem("showShLocation", l="Show Shader Location", c=partial(showShaderLocation, iconButton), p=iconOptions)
    pm.menuItem("iconSubMenu",l="Icon", sm= True, p=iconOptions)
    pm.menuItem("deleteIconMenu",l="Delete Icon", c=partial(deleteIconFile, iconButton))
    deleteItem= pm.menuItem("deleteShader", l="Delete Shader",c=partial(deleteShader, iconButton), p=iconOptions, en=False)
    
    deleteOptions.append(deleteItem)
    iconButtons.append(iconButton)


# Creates an icon for a given asset path.
def createAssetIcon(assetPath=[], iconSize=110, assetIcon="meshToPolygons.png", assetLabel="", parentLayout="allAssetsLayout"):
    iconButton = pm.iconTextButton(i=assetIcon, l=assetLabel, p=parentLayout, st="iconAndTextVertical", sic=iconSize, w=iconSize, h=iconSize+20)
    pm.menuItem("showAsLocation", l="Show Asset Location")
    pass


# Populate with icons
def populateWithIcons(mtlPathList, mtlIconPathList, parentLayout, addToName="", addToIconless=True):
    for i in range(len(mtlPathList)):
        createShaderIcon(shaderPath=mtlPathList[i], shaderIcon=mtlIconPathList[i], shaderLabel=os.path.basename(mtlPathList[i][-1]), parentLayout=parentLayout, addToName=addToName, addToIconless=addToIconless)


# Toggles the ability to delete shaders
def deleteModeToggle(*args):
    global deleteOptions
    
    if pm.shelfLayout("allShadersLayout",q=True, bgc=True)[0] < 0.4:  
        pm.menuItem("deleteMode", e= True, l= "Disable Delete Mode")
        for delOpt in deleteOptions:
            delOpt.setEnable(True)
        pm.shelfLayout("allShadersLayout",e=True, bgc=[.75,0,0])
    else:
        pm.menuItem("deleteMode", e=True, l="Enable Delete Mode")
        
        for delOpt in deleteOptions:
            if delOpt.exists(delOpt):
                delOpt.setEnable(False)
            else:
                deleteOptions.remove(delOpt)
        
        pm.shelfLayout("allShadersLayout",e=True, bgc=[.17,.17,.17])


def createWindow(name="wow", title="wow", width=50, height=50, resToFitCh=True, minb=True, maxb=True, menuBar=True, resizeable=True):
    if pm.window(name, exists=True):
        pm.deleteUI(name)

    newWindow = pm.window(name, t=title, resizeToFitChildren=resToFitCh, mnb=minb, mxb=maxb, mb=menuBar, s=resizeable)
    pm.window(name, e=True, w=width, h=height)
    return newWindow


# Creates a frame
def createFrame(parentLayout, FrName="Frame", label="Label", mWidth=10, collapsed=True, width=345):
    frame = pm.frameLayout(FrName, l=label, cl=collapsed, cll=True, marginHeight=2, marginWidth=mWidth, p=parentLayout, w=width)  
    return frame


# Update all tabs
def refreshShaderTab(*args):
    global globalDirectoryList, iconlessButtons, deleteOptions, iconButtons
    iconButtons = []
    deleteOptions = []
    iconlessButtons = []
    dirList = globalDirectoryList
    """Deletes any existing icons and populates the Tabs with new ones from the chosen shader directories.
    """
    # Delete items from the projectFilter option menu
    pm.optionMenu("projectFilter", e=True, dai=True)
    pm.menuItem(p="projectFilter", l="All")
    
    # Delete all icons in the tab
    existingIcons = pm.shelfLayout("allShadersLayout",q=True, ca=True)
    
    try:
        existingIcons += pm.shelfLayout("allTexturesLayout",q=True, ca=True)
    except:
        pass
    try:
        existingIcons += pm.shelfLayout("allAssetsLayout",q=True, ca=True)
    except:
        pass

    if existingIcons is not None:
        pm.deleteUI(existingIcons)
    
    # Create new icons and frames
    for dir in dirList:
        tab = dir[1]
        dir = dir[0]
        pLists = updatePathList(dir)
        dirName = dir[dir.rfind("/")+1 : len(dir)]
        pm.menuItem(l=dirName, p="projectFilter")  # Add project name to project filter option menu.
            
        if tab == "Shader":
            # Populate "Shaders" tab
            populateWithIcons(pLists[0], pLists[1], "allShadersLayout", addToName=dirName)
        if tab == "Texture":
            # Populate "Textures" tab
            populateWithIcons(pLists[0], pLists[1], "allTexturesLayout", addToName=dirName)
        if tab == "Asset":
            # Populate "Assets" tab
            populateWithIcons(pLists[0], pLists[1], "allAssetsLayout", addToName=dirName)
 
    pm.separator(st="none", h=200, p="allShadersLayout")
    pm.separator(st="none", h=200, p="allTexturesLayout")
    pm.separator(st="none", h=200, p="allAssetsLayout")
    
    # Update list of iconless buttons to be rendered by the menu item command.
    pm.menuItem("renderIconsMItem" , e=True, c=partial(assignRenderIcons, iconlessButtons))


# UI Windows
def renamingWindow(nodes,prefix):
    createWindow(name="renamingWindow", title="Rename Shader",resToFitCh=True, menuBar=False, resizeable=False, width=310)
    pm.columnLayout()
    pm.text(l= "    There are shaders with matching names in the scene.\nPlease add a unique prefix or suffix.")
    pm.separator(st="none", h=10)
    pm.setParent("..")
    pm.rowColumnLayout(nc=2, cs=([1,5],[2,5]))
    pm.text(l="Prefix")
    pm.text(l="Suffix")
    pm.textField("prefixTxf", w=145)
    pm.textField("suffixTxf", w=145)
    
    def renameNodes(nodes, prefix, *args):
        newPrefix = pm.textField("prefixTxf", q=True, tx=True)
        suffix = pm.textField("suffixTxf", q=True, tx=True)
        if newPrefix != "" or suffix != "":
            for node in nodes:
                name = "%s%s" % (node.replace(prefix, newPrefix), suffix)
                pm.rename(node, name)
            pm.deleteUI("renamingWindow")
        else:
            pm.warning("Please add a unique prefix or suffix!")
    
    pm.separator(st="none", h=10)
    pm.separator(st="none", h=10)
    pm.separator(st="none")
    pm.button(l="Rename", w=50, c=partial(renameNodes, nodes, prefix))
    pm.separator(st="none", h=5)
    pm.showWindow("renamingWindow")


def writePathsToConfig(dirListAll, dirListLok, dirListSh):
    # Write changes to config file.    
    global globalDirectoryList, docDir
    globalDirectoryList = dirListAll

    with open(docDirLok, "w") as configFile:
        configFile.write("# Paths of shader directories:\n\n")
        for path in dirListLok:
            configFile.write("%s# %s\n" % (path[1], path[0]))
            
    with open(docDirShared, "w") as configFile:
        configFile.write("# Paths of shader directories:\n\n")
        for path in dirListSh:
            configFile.write("%s# %s\n" % (path[1], path[0]))


def shaderPathListWindow(*args):
    pathTextFields = []  # This variable will be used when writing the new paths to the config file
    
    def copyDirTree(sourceField, dstField, *args):
        source = sourceField.getText()
        dst = dstField.getText()
        
        dirName = os.path.split(source)[1]
        
        if dst == "":
            return 0
        # Copies the content of whatever path is given in the text field to specified new path  
        copytree(source, os.path.join(dst, dirName))
        sourceField.setText(os.path.join(dst, dirName))
        pm.deleteUI('copyPathWindow')
    
    def copyToWindow(pathField, *args):
        createWindow(name="copyPathWindow", title="Copy To", menuBar=False, resizeable=False)
        pm.rowColumnLayout(nc=1)
        pm.rowColumnLayout(nc=2, cs=([1,5], [2,5]))
        pm.separator(st="none", h=3)
        pm.separator(st="none", h=3)
        pm.text(l="Copy To: ")
        dstField = pm.textField("copyDestinationPath", w=400)
        pm.separator(st="none", h=12)
        pm.separator(st="none", h=12)
        pm.setParent('..')
        pm.rowColumnLayout(nc=2, cs=[2,10], co=[1,"left",180])
        pm.button("Cancel", c="pm.deleteUI('copyPathWindow')", w=50)
        pm.button("Copy", c=partial(copyDirTree, pathField, dstField), w=50)
        pm.separator(st="none", h=10)
        pm.showWindow("copyPathWindow")


    # Create text fields
    def pathInputFieldGrp(pathFieldName, parentLayout, saveInConfig="Both", tx="", tab=""):
        pm.rowColumnLayout(nc=5, cs=([1,5],[2,5],[3,5],[4,5],[5,10]),  p=parentLayout)
        pm.text(l="%s Folder:" %tab)
        pathTextField = pm.textField(pathFieldName,w=400, tx=tx)
        
        def createDialog (*args):
            path = pm.fileDialog2(cap="Add %s Directory" % tab, fm=3, okc="Select")
            if path is None:
                pass
            else:
                pathTextField.setText(str(path[0]))
        
        pm.iconTextButton(i="folder-open.png", c=createDialog)
        
        # Option menu for save location
        opMenu = pm.optionMenu("%sConfigMenu" % pathFieldName, w=70)
        pm.menuItem("%sBothConfigMItem" % pathFieldName, l="Both", p=opMenu)
        pm.menuItem("%sSharedConfigMItem" % pathFieldName, l="Shared", p=opMenu)
        pm.menuItem("%sLocalConfigMItem" % pathFieldName, l="Local", p=opMenu)
        pm.optionMenu("%sConfigMenu" % pathFieldName, e=True, v=saveInConfig)
        pm.button(l= "Copy To", c= partial(copyToWindow, pathTextField))
        
        pathTextFields.append((pathTextField, tab, opMenu))   
    
    # Add text field: adds a group of a text field, an option menu and the icon for copying
    def addNewShaderDirPath(tx="", *args):
        tab = pm.tabLayout("dirPathTabs", q=True , tl=True)[pm.tabLayout("dirPathTabs", q=True, sti=True)-1].replace(" Dirs", "")  # "allTabLayouts"["id of selected tab" -1].remove(" Dirs")
        """/\
          /||\This checks if you are currently in the "Shader Dirs", "Texture Dirs" or "Asset Dirs" tab, the "tab" variable can be "Shader" , "Texture" or "Asset"
           ||
                 \||/ "shader" , "texture" or "asset" gets passed as the parent of the text field group being created
                  \/ 
        """
        pathInputFieldGrp("pathField","%sListLayout" % tab.lower(), tx=tx, tab=tab)
        
    # Write changes to config file
    def textFieldsToPathsAndRefresh(pathTextFields, *args):
        dirListLok = []
        dirListSh = []
        dirListAll = set()
        # Extract paths from text fields
        for field in pathTextFields:
            optMenuVal = pm.optionMenu(field[2], q= True, v= True)
            fieldVal = field[0].getText() # The content of the text field
            
            if optMenuVal == "Both":
                if fieldVal != "":
                    dirListLok.append((fieldVal, field[1]))
                    dirListSh.append((fieldVal, field[1]))
                    dirListAll.add((fieldVal, field[1], optMenuVal))  # All paths go in sets
            elif optMenuVal == "Local":
                if fieldVal != "":
                    dirListLok.append((fieldVal, field[1]))
                    dirListAll.add((fieldVal, field[1], optMenuVal))       
            else:
                if fieldVal != "":
                    dirListSh.append((fieldVal, field[1]))
                    dirListAll.add((fieldVal, field[1], optMenuVal))
         
        writePathsToConfig(list(dirListAll), dirListLok, dirListSh)
        refreshShaderTab()

    createWindow(name="pathListWindow", title="Directory List",resToFitCh=True, menuBar=False, resizeable=False, width=650)
    pm.columnLayout("dirPathColumns",w=680)
    pm.tabLayout("dirPathTabs")
    pm.scrollLayout("shaderListLayout", w=680,h=200, p="dirPathTabs")
    pm.scrollLayout("textureListLayout", w=680,h=200, p="dirPathTabs")
    pm.scrollLayout("assetListLayout", w=680,h=200, p="dirPathTabs")
    pm.tabLayout("dirPathTabs", e=True, tli=([1,"Shader Dirs"],[2,"Texture Dirs"], [3,"Asset Dirs"]))
    
    #############
    pathInputFieldGrp("defaultShaderPathField","shaderListLayout", tab="Shader")
    pathInputFieldGrp("defaultTexturePathField","textureListLayout", tab="Texture")
    pathInputFieldGrp("defaultAssetPathField","assetListLayout", tab="Asset")
    
    ############
    pm.rowColumnLayout(nc= 2, cs=[2,10], co=[1,"left", 210], p= "dirPathColumns")
    pm.button(l="Add New", w=75, c= partial(addNewShaderDirPath,""))
    pm.button(l="Refresh", w=75, c=partial(textFieldsToPathsAndRefresh, pathTextFields))
    pm.separator(st="none",h=10)
    pm.separator(st="none",h=10)
    
    # Add paths from config file to text fields
    global globalDirectoryList
    if len(globalDirectoryList) > 0:
        for path in globalDirectoryList:
            if pm.textField("default%sPathField" %path[1], q=True, tx=True) == "":
                pm.textField("default%sPathField" %path[1], e=True, tx=path[0])
                pm.optionMenu("default%sPathFieldConfigMenu" %path[1], e=True, v=path[2])
            else:
                pathInputFieldGrp("pathField","%sListLayout" % path[1].lower(), saveInConfig=path[2] , tx=path[0], tab=path[1])
    
    pm.showWindow("pathListWindow")


def createUI():

    createWindow(name="mainWindow", title="IS_ML")
    pm.menu("utilityMenu", l="Utilities", p="mainWindow")
    pm.menuItem(l="Directory List", c=partial(shaderPathListWindow))
    pm.menuItem(l="Export Selected Shading Group", c=partial(exportOptionsWindow))
    pm.menuItem(l="Refresh Shader List", c=partial(refreshShaderTab))
    pm.menuItem(l="Render Icons", sm=True)
    pm.menuItem("renderIconsMItem" ,l="Render using Vray")
    pm.menuItem("deleteMode",l="Enable Delete Mode", p="utilityMenu", c=partial(deleteModeToggle))
    pm.menuItem("copyTexturesSubMenu", l="Move all textures to shader location", p="utilityMenu", sm=True)
    pm.menuItem("copyTextures", l="Copy and relink all textures to shader dir" , p="copyTexturesSubMenu", c=partial(MoveAllTexturesHandler))
    
    
    
    # Commands for the filter options
    def filterC(*args):
        iconList = pm.shelfLayout("allShadersLayout", q=True, ca=True)[:-1]
        try:
            iconList += pm.shelfLayout("allTexturesLayout", q=True, ca=True)[:-1]
        except:
            pass
        try:
            iconList += pm.shelfLayout("allAssetsLayout", q=True, ca=True)[:-1]
        except:
            pass
        project = pm.optionMenu("projectFilter", q=True, v=True)
        tag = pm.optionMenu("tagOpMenu", q=True, v=True)
        searchStr = pm.textField("shaderSearchField",q=True, tx=True)
        filterIcons(iconList,project, tag, searchStr)
    
    #Filter options
    pm.rowColumnLayout(nc=2)
    
    # Filter by project
    pm.text(l= "Project: ", w=70, al= "right")
    pm.optionMenu("projectFilter", cc= partial(filterC))
    pm.menuItem(l="All")
    pm.separator(h=10,st="none")
    pm.separator(h=10,st="none")
    # Material Tags
    pm.text(l="Type: ", w=50, al="right")
    pm.optionMenu("tagOpMenu", cc=partial(filterC))
    pm.menuItem(l="All")
    addTagOptions("tagOpMenu")
    # Search field
    pm.text(l= "Name: ", al="right")
    pm.textField("shaderSearchField", w=280, ec=partial(filterC), sf=True, aie=True)
    pm.setParent("..")
    # Main tab layout
    pm.tabLayout("ISMLTabs")
    # Adjustable grid with shader icons
    pm.shelfLayout("allShadersLayout", bgc=[.17,.17,.17], w=350,h=940)
    pm.setParent("..")
    pm.shelfLayout("allTexturesLayout", bgc=[.17,.17,.17], w=350,h=940)
    pm.setParent("..")
    pm.shelfLayout("allAssetsLayout", bgc=[.17,.17,.17], w=350,h=940)
    pm.tabLayout("ISMLTabs",e=True, tli=([1,"Shaders"],[2,"Textures"],[3,"Assets"]))
    # update shader list
    refreshShaderTab()
    pm.showWindow("mainWindow")
    if pm.dockControl("materialLibDock", q=True, ex=True):
        pm.deleteUI("materialLibDock")
    pm.dockControl("materialLibDock",l="IS_ML work", a="right", con="mainWindow")


createUI()